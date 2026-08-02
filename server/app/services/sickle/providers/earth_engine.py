from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from shapely.geometry import mapping

from app.core.exceptions import DomainError

from ..contracts import CropInputs, DetailedObservation, Grid, ObservationQuality
from ..crop import DAY_POSITIONS, MONTHS, S1_BANDS, S2_BANDS
from ..geometry import ValidatedGeometry


class EarthEngineProvider:
    name = "earth_engine"
    live_data = True

    def __init__(self, project_id: str, cache_root: Path, cache_ttl: int, retries: int, timeout_seconds: int = 120, enabled: bool = True, auth_mode: str = "adc", endpoint: str = "https://earthengine.googleapis.com", credential_path: str | None = None, roi_version: int = 1):
        self.project_id = project_id
        self.cache_root = cache_root
        self.cache_ttl = cache_ttl
        self.retries = retries
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self.auth_mode = auth_mode
        self.endpoint = endpoint
        self.credential_path = credential_path
        self.roi_version = roi_version
        self.initialized = False
        self.error: str | None = None

    def initialize(self) -> None:
        if not self.enabled or not self.project_id:
            self.error = "Earth Engine is disabled or project ID is missing."
            return
        if self.auth_mode != "adc":
            self.error = "Only Earth Engine Application Default Credentials are supported."
            return
        try:
            import ee
            import google.auth
            if self.credential_path:
                from google.oauth2 import service_account
                path = Path(self.credential_path)
                if not path.is_absolute() or not path.is_file():
                    raise RuntimeError("Service-account credential path must be an existing absolute path")
                credentials = service_account.Credentials.from_service_account_file(path, scopes=ee.oauth.SCOPES)
            else:
                credentials, _ = google.auth.default(scopes=ee.oauth.SCOPES)
            ee.Initialize(credentials=credentials, project=self.project_id, url=self.endpoint)
            ee.data.setDeadline(self.timeout_seconds * 1000)
            self.initialized = True
            self.error = None
        except Exception:
            self.error = "Earth Engine authentication or initialization failed."

    def readiness(self) -> dict:
        return {"ready": self.initialized, "provider": self.name, "live_data": True, "error": self.error}

    def _require_ready(self):
        if not self.initialized:
            raise DomainError("EARTH_ENGINE_NOT_READY", self.error or "Earth Engine is not ready.", 503)
        import ee
        return ee

    def _grid(self, geometry: ValidatedGeometry) -> tuple[Grid, np.ndarray]:
        affine = Affine(*geometry.grid_transform)
        mask = geometry_mask([mapping(geometry.geometry)], out_shape=(32, 32), transform=affine, invert=True)
        grid = Grid(geometry.grid_crs, (affine.a, affine.b, affine.c, affine.d, affine.e, affine.f))
        if not mask.any():
            raise DomainError("NO_OVERLAPPING_RASTER", "The field does not cover a target-grid pixel.")
        if mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any():
            raise DomainError("FIELD_DOES_NOT_FIT_PATCH", "The field reaches the target patch edge.")
        return grid, mask

    @staticmethod
    def _request_grid(grid: Grid) -> dict:
        a, b, c, d, e, f = grid.transform
        return {
            "dimensions": {"width": 32, "height": 32},
            "affineTransform": {"scaleX": a, "shearX": b, "translateX": c, "shearY": d, "scaleY": e, "translateY": f},
            "crsCode": grid.crs,
        }

    def _compute(self, image, bands: list[str], grid: Grid, request_id: str) -> np.ndarray:
        ee = self._require_ready()
        request = {"expression": image.select(bands), "fileFormat": "NUMPY_NDARRAY", "bandIds": bands, "grid": self._request_grid(grid), "workloadTag": request_id}
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                result = ee.data.computePixels(request)
                if result.dtype.names:
                    array = np.stack([result[name] for name in bands], axis=0)
                else:
                    array = np.asarray(result)
                    if array.shape[-1] == len(bands):
                        array = np.moveaxis(array, -1, 0)
                return np.nan_to_num(array, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.25 * (2 ** attempt))
        message = str(last_error).lower()
        if "timeout" in message or "timed out" in message or "deadline" in message:
            code = "EARTH_ENGINE_TIMEOUT"
        elif "quota" in message or "429" in message:
            code = "EARTH_ENGINE_QUOTA_EXCEEDED"
        else:
            code = "EARTH_ENGINE_REQUEST_FAILED"
        raise DomainError(code, "Earth Engine pixel retrieval failed.", 503) from last_error

    def _cache_key(self, geometry: ValidatedGeometry, year: int, grid: Grid) -> str:
        payload = {"geometry_hash": geometry.geometry_hash, "year": year, "roi_version": self.roi_version, "months": MONTHS, "s1": S1_BANDS, "s2": S2_BANDS, "grid": grid.__dict__, "preprocessing": "sickle-cauvery-v2-s2-cloud15", "s2_scene_cloud_limit": 15, "collections": ["COPERNICUS/S1_GRD", "COPERNICUS/S2_SR_HARMONIZED"]}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def crop_inputs(self, geometry: ValidatedGeometry, year: int, request_id: str) -> CropInputs:
        ee = self._require_ready()
        grid, field_mask = self._grid(geometry)
        cache_key = self._cache_key(geometry, year, grid)
        cache_path = self.cache_root / f"{cache_key}.npz"
        if cache_path.is_file() and time.time() - cache_path.stat().st_mtime <= self.cache_ttl:
            with np.load(cache_path, allow_pickle=False) as cached:
                qualities = [ObservationQuality(**item) for item in json.loads(str(cached["quality_json"].item()))]
                return CropInputs(cached["s1"], cached["s1_dates"], cached["s1_months"].tolist(), cached["s2"], cached["s2_dates"], cached["s2_months"].tolist(), cached["field_mask"].astype(bool), grid, qualities, self.name, True, True)
        field = ee.Geometry(mapping(geometry.patch_footprint))
        s1_samples, s2_samples, s1_dates, s2_dates, s1_months, s2_months, quality = [], [], [], [], [], [], []
        for month_index, month in enumerate(MONTHS, start=6):
            start = ee.Date.fromYMD(year, month_index, 1)
            end = start.advance(1, "month")
            s1_collection = (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(field).filterDate(start, end).filter(ee.Filter.eq("instrumentMode", "IW")).filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV")).filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH")))
            s2_collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(field).filterDate(start, end).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 15)))
            for sensor, collection, bands, samples, dates, used in (("S1", s1_collection, S1_BANDS, s1_samples, s1_dates, s1_months), ("S2", s2_collection, S2_BANDS, s2_samples, s2_dates, s2_months)):
                empty = ee.Image.constant([0] * len(bands)).rename(bands)
                composite = ee.Image(ee.Algorithms.If(collection.size().gt(0), collection.median(), empty))
                patch = self._compute(composite, bands, grid, request_id)
                zero_fraction = float(np.mean(patch[0] == 0))
                keep = zero_fraction < 0.25
                quality.append(ObservationQuality(sensor, month, DAY_POSITIONS[month], keep, zero_fraction, rejection_reason=None if keep else "ZERO_FRACTION_LIMIT"))
                if keep:
                    samples.append(patch); dates.append(DAY_POSITIONS[month]); used.append(month)
        if not s1_samples:
            raise DomainError("INSUFFICIENT_SENTINEL1", "No usable Sentinel-1 crop observation is available.")
        if not s2_samples:
            raise DomainError("INSUFFICIENT_SENTINEL2", "No usable Sentinel-2 crop observation is available.")
        inputs = CropInputs(np.stack(s1_samples).astype(np.float32), np.asarray(s1_dates, dtype=np.int64), s1_months, np.stack(s2_samples).astype(np.float32), np.asarray(s2_dates, dtype=np.int64), s2_months, field_mask, grid, quality, self.name, True)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix(f".{os.getpid()}.tmp.npz")
        np.savez_compressed(temporary, s1=inputs.s1, s1_dates=inputs.s1_dates, s1_months=np.asarray(s1_months), s2=inputs.s2, s2_dates=inputs.s2_dates, s2_months=np.asarray(s2_months), field_mask=field_mask, quality_json=np.asarray(json.dumps([item.__dict__ for item in quality])))
        os.replace(temporary, cache_path)
        return inputs

    def detailed_series(self, geometry: ValidatedGeometry, year: int, request_id: str) -> list[DetailedObservation]:
        ee = self._require_ready()
        region = ee.Geometry(mapping(geometry.geometry))
        start, end = f"{year}-01-01", f"{year + 1}-01-01"
        reducer = ee.Reducer.median().combine(ee.Reducer.stdDev(), sharedInputs=True).combine(ee.Reducer.count(), sharedInputs=True)

        def s1_feature(image):
            values = image.select(["VV", "VH", "angle"]).addBands(image.select("VV").subtract(image.select("VH")).rename("VV_minus_VH")).reduceRegion(reducer=reducer, geometry=region, scale=10, maxPixels=100000)
            return ee.Feature(None, values).set({"date": image.date().format("YYYY-MM-dd"), "source_image_id": image.id(), "orbit_pass": image.get("orbitProperties_pass"), "orbit_number": image.get("relativeOrbitNumber_start")})

        def s2_feature(image):
            ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
            ndmi = image.normalizedDifference(["B8", "B11"]).rename("NDMI")
            ndwi = image.normalizedDifference(["B3", "B8"]).rename("NDWI")
            values = ndvi.addBands(ndmi).addBands(ndwi).reduceRegion(reducer=reducer, geometry=region, scale=10, maxPixels=100000)
            return ee.Feature(None, values).set({"date": image.date().format("YYYY-MM-dd"), "source_image_id": image.id(), "scene_cloud_percentage": image.get("CLOUDY_PIXEL_PERCENTAGE")})

        with ee.data.workloadTagContext(request_id):
            s1 = (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(region).filterDate(start, end).filter(ee.Filter.eq("instrumentMode", "IW")).filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV")).filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH")).map(s1_feature).getInfo())
            s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate(start, end).map(s2_feature).getInfo()
        output = []
        for sensor, collection in (("S1", s1), ("S2", s2)):
            for feature in collection.get("features", []):
                values = dict(feature.get("properties", {})); date = values.pop("date", None); source = values.pop("source_image_id", None)
                if date:
                    output.append(DetailedObservation(sensor, date, values, source))
        if not output:
            raise DomainError("DETAILED_TIMESERIES_UNAVAILABLE", "Earth Engine returned no detailed observations.")
        return output
