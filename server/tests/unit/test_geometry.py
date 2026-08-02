import pytest
from shapely.geometry import box

from app.core.exceptions import DomainError
from app.services.sickle.geometry import canonicalize_geojson_bytes, validate_geometry

pytestmark = pytest.mark.unit


def validate(geometry, roi=box(78.0, 10.0, 80.0, 12.0)):
    return validate_geometry(geometry, max_vertices=10_000, min_area_m2=100, max_area_m2=78_400, max_width_m=280, max_height_m=280, roi=roi)


def test_small_inside_polygon_is_accepted():
    result = validate({"type": "Polygon", "coordinates": [[[79.0, 11.0], [79.001, 11.0], [79.001, 11.001], [79.0, 11.001], [79.0, 11.0]]]})
    assert result.area_m2 >= 100
    assert result.field_pixel_count > 0


def test_outside_polygon_is_rejected():
    with pytest.raises(DomainError, match="outside") as error:
        validate({"type": "Polygon", "coordinates": [[[82.0, 15.0], [82.001, 15.0], [82.001, 15.001], [82.0, 15.001], [82.0, 15.0]]]})
    assert error.value.code == "OUTSIDE_SUPPORTED_ROI"


def test_self_intersection_is_not_repaired():
    with pytest.raises(DomainError) as error:
        validate({"type": "Polygon", "coordinates": [[[79, 11], [79.001, 11.001], [79.001, 11], [79, 11.001], [79, 11]]]})
    assert error.value.code == "INVALID_GEOMETRY"


def test_roi_checksum_is_stable_across_whitespace_and_key_order():
    compact = b'{"type":"Polygon","coordinates":[[[79.0,11.0],[79.001,11.0],[79.001,11.001],[79.0,11.001],[79.0,11.0]]]}'
    expanded = b'{\n  "coordinates": [\n    [\n      [79.0, 11.0],\n      [79.001, 11.0],\n      [79.001, 11.001],\n      [79.0, 11.001],\n      [79.0, 11.0]\n    ]\n  ],\n  "type": "Polygon"\n}\n'
    assert canonicalize_geojson_bytes(compact)[1] == canonicalize_geojson_bytes(expanded)[1]
