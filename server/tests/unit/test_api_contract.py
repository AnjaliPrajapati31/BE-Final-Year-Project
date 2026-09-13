import pytest
from datetime import date
from pydantic import ValidationError

from app.main import app
from app.schemas.field_analysis import FieldAnalysisRequest
from app.schemas.water import FieldWaterProfileUpdate, IrrigationEventCreate

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
    assert "/api/v1/fields/{field_id}/irrigation-events" in paths
    assert "/api/v1/fields/{field_id}/water-profile" in paths
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


def test_water_input_contract_rejects_future_events_and_invalid_soil_order():
    with pytest.raises(ValidationError):
        IrrigationEventCreate.model_validate({
            "event_date": date.today().replace(year=date.today().year + 1),
            "amount": 10, "unit": "mm",
        })
    with pytest.raises(ValidationError):
        FieldWaterProfileUpdate.model_validate({"field_capacity": 0.2, "wilting_point": 0.3})


def test_cycle_hints_must_match_analysis_year_and_order():
    payload = {
        "field_id": "HINT_TEST",
        "geometry": {"type": "Polygon", "coordinates": [[[79.316, 10.867], [79.317, 10.867], [79.317, 10.868], [79.316, 10.868], [79.316, 10.867]]]},
        "year": 2025,
    }
    with pytest.raises(ValidationError):
        FieldAnalysisRequest.model_validate({**payload, "sowing_date_hint": "2024-06-01"})
    with pytest.raises(ValidationError):
        FieldAnalysisRequest.model_validate({**payload, "sowing_date_hint": "2025-07-01", "transplanting_date_hint": "2025-06-15"})
