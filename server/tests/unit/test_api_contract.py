import pytest
from fastapi.testclient import TestClient
from datetime import date
from pydantic import ValidationError

from app.main import app
from app.schemas.field_analysis import FieldAnalysisRequest
from app.schemas.water import (
    FieldWaterProfileUpdate,
    IrrigationEventCreate,
    IrrigationHistoryCoverageUpdate,
    WaterObservationCreate,
)

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
    assert "/api/v1/fields/{field_id}/water-observations" in paths
    assert "/api/v1/fields/{field_id}/irrigation-history-coverage" in paths
    assert "/api/v1/analyses/{request_id}/explanation" in paths
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


def test_water_observation_units_and_history_coverage_are_strict():
    observation = WaterObservationCreate.model_validate({
        "observed_at": "2025-06-01T08:00:00+05:30",
        "observation_type": "ponded_depth",
        "value": 25,
        "unit": "mm",
        "method": "field ruler",
    })
    assert observation.observed_at.utcoffset().total_seconds() == 0
    with pytest.raises(ValidationError):
        WaterObservationCreate.model_validate({
            "observed_at": "2025-06-01T08:00:00+05:30",
            "observation_type": "volumetric_soil_water",
            "value": 0.3,
            "unit": "m3/m3",
            "method": "probe",
        })
    with pytest.raises(ValidationError):
        IrrigationHistoryCoverageUpdate.model_validate({
            "coverage_status": "complete", "coverage_start": "2025-06-10", "coverage_end": "2025-06-01",
        })


def test_validation_errors_distinguish_analysis_geometry_from_other_forms():
    client = TestClient(app)
    analysis = client.post("/api/v1/fields/analyze", json={})
    assert analysis.status_code == 422
    assert analysis.json()["error"]["code"] == "INVALID_GEOMETRY"

    irrigation = client.post("/api/v1/fields/TEST/irrigation-events", json={})
    assert irrigation.status_code == 422
    assert irrigation.json()["error"]["code"] == "INVALID_REQUEST"
