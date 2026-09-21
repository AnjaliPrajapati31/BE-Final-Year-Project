from types import SimpleNamespace

import pytest
from shapely.geometry import Polygon, shape

from app.core.exceptions import DomainError
from app.routers.fields import approved_coverage

pytestmark = pytest.mark.unit


def test_coverage_returns_loaded_approved_geometry():
    roi = Polygon([(79, 10), (80, 10), (80, 11), (79, 10)])
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        roi=roi, dependencies={"roi_resource": {"ready": True, "sha256": "approved"}},
    )))
    result = approved_coverage(request)
    assert result["success"]
    assert shape(result["data"]["geometry"]).equals(roi)
    assert result["data"]["properties"]["sha256"] == "approved"


@pytest.mark.parametrize("ready", [False, None])
def test_unverified_roi_is_never_exposed(ready):
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        roi=Polygon([(79, 10), (80, 10), (80, 11), (79, 10)]),
        dependencies={"roi_resource": {"ready": ready}},
    )))
    with pytest.raises(DomainError):
        approved_coverage(request)
