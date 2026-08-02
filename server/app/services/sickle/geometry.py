from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyproj import CRS, Transformer
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
from shapely.ops import transform
from shapely.validation import explain_validity

from app.core.exceptions import DomainError

# Frozen from the original June Sentinel-1 raster grid used to build the
# supplied PILOT_001 known-answer NPZ. All production fields snap to this
# lattice so Earth Engine and the original export use identical pixels.
GRID_CRS = "EPSG:4326"
GRID_PIXEL_SIZE_DEGREES = 8.983152841195215e-05
GRID_REFERENCE_LEFT = 79.31549036993538
GRID_REFERENCE_TOP = 10.86925561173256


@dataclass(frozen=True)
class ValidatedGeometry:
    geometry: MultiPolygon
    patch_footprint: Polygon
    geometry_json: str
    patch_json: str
    geometry_hash: str
    area_m2: float
    width_m: float
    height_m: float
    utm_crs: str
    field_pixel_count: int
    grid_transform: tuple[float, float, float, float, float, float]
    grid_crs: str


def _vertex_count(value: Any) -> int:
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
            return 1
        return sum(_vertex_count(item) for item in value)
    return 0


def _finite_coordinates(value: Any) -> None:
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
            lon, lat = float(value[0]), float(value[1])
            if not math.isfinite(lon) or not math.isfinite(lat):
                raise DomainError("INVALID_GEOMETRY", "Coordinates must be finite.")
            if not -180 <= lon <= 180 or not -90 <= lat <= 90:
                raise DomainError("INVALID_GEOMETRY", "Coordinates must be WGS84 longitude/latitude.")
            return
        for item in value:
            _finite_coordinates(item)


def _as_multipolygon(geometry: Polygon | MultiPolygon) -> MultiPolygon:
    return geometry if isinstance(geometry, MultiPolygon) else MultiPolygon([geometry])


def canonicalize_geojson_bytes(raw: bytes) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DomainError("ROI_CONFIGURATION_INVALID", "Cauvery ROI resource is unreadable.", 503) from exc
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return payload, hashlib.sha256(canonical).hexdigest()


def validate_geometry(
    geometry_mapping: dict[str, Any],
    *,
    max_vertices: int,
    min_area_m2: float,
    max_area_m2: float,
    max_width_m: float,
    max_height_m: float,
    roi: Polygon | MultiPolygon | None,
) -> ValidatedGeometry:
    geometry_type = geometry_mapping.get("type")
    if geometry_type not in {"Polygon", "MultiPolygon"}:
        raise DomainError("UNSUPPORTED_GEOMETRY_TYPE", "Only Polygon and MultiPolygon are supported.")
    if "crs" in geometry_mapping:
        raise DomainError("UNSUPPORTED_CRS", "Submit WGS84 GeoJSON without a crs member.")
    coordinates = geometry_mapping.get("coordinates")
    if not coordinates:
        raise DomainError("EMPTY_GEOMETRY", "Geometry is empty.")
    if _vertex_count(coordinates) > max_vertices:
        raise DomainError("TOO_MANY_VERTICES", "Geometry has too many vertices.")
    _finite_coordinates(coordinates)
    try:
        parsed = shape(geometry_mapping)
    except (TypeError, ValueError, IndexError) as exc:
        raise DomainError("INVALID_GEOMETRY", "Coordinate nesting is invalid.") from exc
    if parsed.is_empty:
        raise DomainError("EMPTY_GEOMETRY", "Geometry is empty.")
    if not isinstance(parsed, (Polygon, MultiPolygon)) or not parsed.is_valid:
        reason = explain_validity(parsed)
        raise DomainError("INVALID_GEOMETRY", f"Geometry is invalid: {reason}.")
    center = parsed.centroid
    zone = int((center.x + 180) // 6) + 1
    epsg = 32600 + zone if center.y >= 0 else 32700 + zone
    utm = CRS.from_epsg(epsg)
    forward = Transformer.from_crs(4326, utm, always_xy=True).transform
    projected = transform(forward, parsed)
    minx, miny, maxx, maxy = projected.bounds
    area, width, height = float(projected.area), float(maxx - minx), float(maxy - miny)
    if area < min_area_m2:
        raise DomainError("FIELD_TOO_SMALL", f"Field area must be at least {min_area_m2:g} m².")
    if area > max_area_m2 or width > max_width_m or height > max_height_m:
        raise DomainError("FIELD_TOO_LARGE", "Field exceeds the supported 32×32 patch limits.")
    centroid = parsed.centroid
    center_column = math.floor((centroid.x - GRID_REFERENCE_LEFT) / GRID_PIXEL_SIZE_DEGREES)
    center_row = math.floor((GRID_REFERENCE_TOP - centroid.y) / GRID_PIXEL_SIZE_DEGREES)
    left = GRID_REFERENCE_LEFT + (center_column - 16) * GRID_PIXEL_SIZE_DEGREES
    top = GRID_REFERENCE_TOP - (center_row - 16) * GRID_PIXEL_SIZE_DEGREES
    right = left + 32 * GRID_PIXEL_SIZE_DEGREES
    bottom = top - 32 * GRID_PIXEL_SIZE_DEGREES
    patch = box(left, bottom, right, top)
    if not patch.covers(parsed):
        raise DomainError("FIELD_DOES_NOT_FIT_PATCH", "The complete field does not fit the 32×32 patch.")
    grid_affine = Affine(GRID_PIXEL_SIZE_DEGREES, 0, left, 0, -GRID_PIXEL_SIZE_DEGREES, top)
    field_mask = geometry_mask(
        [mapping(parsed)],
        out_shape=(32, 32),
        transform=grid_affine,
        invert=True,
    )
    if not field_mask.any():
        raise DomainError("NO_OVERLAPPING_RASTER", "The field does not cover a target-grid pixel.")
    if field_mask[0].any() or field_mask[-1].any() or field_mask[:, 0].any() or field_mask[:, -1].any():
        raise DomainError("FIELD_DOES_NOT_FIT_PATCH", "The field reaches the 32×32 patch edge.")
    multi = _as_multipolygon(parsed)
    if roi is not None and (not roi.covers(multi) or not roi.covers(patch)):
        raise DomainError(
            "OUTSIDE_SUPPORTED_ROI",
            "This field is outside the supported Cauvery Delta pilot region.",
        )
    geometry_json = json.dumps(mapping(multi), separators=(",", ":"), sort_keys=True)
    patch_json = json.dumps(mapping(patch), separators=(",", ":"), sort_keys=True)
    return ValidatedGeometry(
        geometry=multi,
        patch_footprint=patch,
        geometry_json=geometry_json,
        patch_json=patch_json,
        geometry_hash=hashlib.sha256(geometry_json.encode()).hexdigest(),
        area_m2=area,
        width_m=width,
        height_m=height,
        utm_crs=utm.to_string(),
        field_pixel_count=int(field_mask.sum()),
        grid_transform=(grid_affine.a, grid_affine.b, grid_affine.c, grid_affine.d, grid_affine.e, grid_affine.f),
        grid_crs=GRID_CRS,
    )


def load_roi(path: Path) -> tuple[Polygon | MultiPolygon, str]:
    if not path.is_file():
        raise DomainError("ROI_CONFIGURATION_INVALID", "Cauvery ROI resource is missing.", 503)
    raw = path.read_bytes()
    try:
        payload, checksum = canonicalize_geojson_bytes(raw)
        geometry_payload = payload.get("geometry") if payload.get("type") == "Feature" else payload
        roi = shape(geometry_payload)
    except (TypeError, ValueError) as exc:
        raise DomainError("ROI_CONFIGURATION_INVALID", "Cauvery ROI resource is unreadable.", 503) from exc
    if not isinstance(roi, (Polygon, MultiPolygon)) or roi.is_empty or not roi.is_valid:
        raise DomainError("ROI_CONFIGURATION_INVALID", "Cauvery ROI resource is invalid.", 503)
    return roi, checksum
