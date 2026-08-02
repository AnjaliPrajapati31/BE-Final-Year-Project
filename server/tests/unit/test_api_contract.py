import pytest
from datetime import date
from pydantic import ValidationError

from app.main import app
from app.schemas.field_analysis import FieldAnalysisRequest

pytestmark = pytest.mark.unit


def test_public_schema_cannot_select_provider_or_collections():
    schema = app.openapi()["components"]["schemas"]["FieldAnalysisRequest"]
    properties = schema["properties"]
    assert "provider" not in properties
    assert "collection_id" not in properties
    assert "bands" not in properties
    assert schema["additionalProperties"] is False


def test_required_public_routes_exist():
    paths = app.openapi()["paths"]
    assert "/api/v1/fields/analyze" in paths
    assert "/api/v1/analyses/{request_id}" in paths
    assert "/api/v1/fields/{field_id}/analyses" in paths
    assert "/health/ready" in paths


def test_current_season_is_allowed_but_future_season_is_rejected():
    payload = {
        "field_id": "CURRENT_TEST",
        "geometry": {"type": "Polygon", "coordinates": [[[79.316, 10.867], [79.317, 10.867], [79.317, 10.868], [79.316, 10.868], [79.316, 10.867]]]},
        "year": date.today().year,
    }
    assert FieldAnalysisRequest.model_validate(payload).year == date.today().year
    with pytest.raises(ValidationError):
        FieldAnalysisRequest.model_validate({**payload, "year": date.today().year + 1})
