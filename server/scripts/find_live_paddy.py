from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

from shapely.geometry import Polygon, mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.pool import Database
from app.db.repositories import AnalysisRepository
from app.ml.sickle.runtime import SickleRuntime
from app.schemas.field_analysis import FieldAnalysisRequest
from app.services.sickle.analysis import AnalysisService
from app.services.sickle.artifacts import ArtifactWriter
from app.services.sickle.crop import summarize_crop, validate_crop_inputs
from app.services.sickle.geometry import load_roi, validate_geometry
from app.services.sickle.providers.earth_engine import EarthEngineProvider


def square(longitude: float, latitude: float, half_size_degrees: float = 0.00032) -> Polygon:
    return Polygon(
        [
            (longitude - half_size_degrees, latitude - half_size_degrees),
            (longitude + half_size_degrees, latitude - half_size_degrees),
            (longitude + half_size_degrees, latitude + half_size_degrees),
            (longitude - half_size_degrees, latitude + half_size_degrees),
            (longitude - half_size_degrees, latitude - half_size_degrees),
        ]
    )


def main() -> None:
    import ee

    today = date.today()
    roi, _ = load_roi(settings.path(settings.CAUVERY_ROI_PATH))
    provider = EarthEngineProvider(
        settings.EARTH_ENGINE_PROJECT_ID or "",
        settings.path(settings.EARTH_ENGINE_CACHE_ROOT),
        settings.EARTH_ENGINE_CACHE_TTL_SECONDS,
        settings.EARTH_ENGINE_MAX_RETRIES,
        settings.EARTH_ENGINE_REQUEST_TIMEOUT_SECONDS,
        settings.EARTH_ENGINE_ENABLED,
        settings.EARTH_ENGINE_AUTH_MODE,
        settings.EARTH_ENGINE_ENDPOINT,
        settings.GOOGLE_APPLICATION_CREDENTIALS,
        settings.CAUVERY_ROI_VERSION,
    )
    provider.initialize()
    if not provider.initialized:
        raise SystemExit("Earth Engine is not ready.")
    runtime = SickleRuntime.load(settings.path(settings.SICKLE_CHECKPOINT_PATH), "cpu", 1)
    database = Database(
        settings.DATABASE_URL or "",
        settings.DATABASE_POOL_MIN_SIZE,
        settings.DATABASE_POOL_MAX_SIZE,
        settings.DATABASE_CONNECT_TIMEOUT_SECONDS,
    )
    database.open()
    repository = AnalysisRepository(database.pool, settings.CAUVERY_ROI_CODE)
    try:
        region = ee.Geometry(mapping(roi))
        optical = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(f"{today.year}-06-01", (today + timedelta(days=1)).isoformat())
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 15))
        )
        ndvi = optical.median().normalizedDifference(["B8", "B4"]).rename("NDVI")
        sampled = ndvi.sample(region=region, scale=400, numPixels=300, seed=20260802, geometries=True, tileScale=4).getInfo()
        candidates = []
        for feature in sampled.get("features", []):
            coordinates = feature.get("geometry", {}).get("coordinates")
            value = feature.get("properties", {}).get("NDVI")
            if coordinates and value is not None and -1 <= float(value) <= 1:
                candidates.append((float(value), float(coordinates[0]), float(coordinates[1])))
        candidates.sort(reverse=True)

        attempts = []
        for index, (ndvi_value, longitude, latitude) in enumerate(candidates[:24], start=1):
            polygon = square(longitude, latitude)
            try:
                geometry = validate_geometry(
                    mapping(polygon),
                    max_vertices=settings.FIELD_MAX_VERTICES,
                    min_area_m2=settings.FIELD_MIN_AREA_M2,
                    max_area_m2=settings.FIELD_MAX_AREA_M2,
                    max_width_m=settings.FIELD_MAX_WIDTH_M,
                    max_height_m=settings.FIELD_MAX_HEIGHT_M,
                    roi=roi,
                )
                repository.verify_roi(geometry.geometry_json, geometry.patch_json)
                inputs = provider.crop_inputs(geometry, today.year, f"live-paddy-search-{index}")
                validate_crop_inputs(inputs)
                crop = summarize_crop(runtime.infer(inputs.s1, inputs.s1_dates, inputs.s2, inputs.s2_dates), inputs.field_mask, inputs)
            except Exception as exc:
                attempts.append({"rank": index, "ndvi": ndvi_value, "location": [longitude, latitude], "error": getattr(exc, "code", type(exc).__name__)})
                continue
            attempts.append(
                {
                    "rank": index,
                    "ndvi": ndvi_value,
                    "location": [longitude, latitude],
                    "crop": crop["class_label"],
                    "paddy_probability": crop["paddy_probability"],
                    "paddy_pixel_fraction": crop["paddy_pixel_fraction"],
                    "s1_months": crop["s1_months_used"],
                    "s2_months": crop["s2_months_used"],
                }
            )
            print(json.dumps(attempts[-1]))
            if crop["class_label"] == "Paddy":
                command = FieldAnalysisRequest.model_validate(
                    {"field_id": f"LIVE_PADDY_{today.year}_{index:02d}", "geometry": mapping(polygon), "year": today.year}
                )
                service = AnalysisService(settings, roi, repository, provider, runtime, ArtifactWriter(settings.path(settings.SICKLE_ARTIFACT_ROOT), False))
                result = service.analyze(command)
                print(json.dumps({"model_predicted_not_ground_truth": True, "selected_ndvi": ndvi_value, "location": [longitude, latitude], "analysis": result}, indent=2, default=str))
                return
        raise SystemExit(json.dumps({"message": "No model-predicted Paddy candidate found in bounded search.", "attempts": attempts}, indent=2))
    finally:
        database.close()


if __name__ == "__main__":
    main()
