import pytest

from app.services.sickle.contracts import DetailedObservation
from app.services.sickle.stage import estimate_stage, skipped_non_paddy

pytestmark = pytest.mark.unit


def test_non_paddy_is_skipped():
    assert skipped_non_paddy()["reason_code"] == "NON_PADDY_STAGE_SKIPPED"


def test_latest_maximum_is_not_a_confirmed_peak():
    dates = ["2025-08-01", "2025-08-12", "2025-08-23", "2025-09-03", "2025-09-14", "2025-09-25", "2025-10-06", "2025-10-11", "2025-10-31"]
    ndvi = [0.65, 0.50, 0.32, 0.15, 0.10, 0.12, 0.05, 0.27, 0.79]
    observations = [DetailedObservation("S2", date, {"NDVI_median": value, "NDMI_median": 0.2, "valid_pixel_count": 26}) for date, value in zip(dates, ndvi)]
    observations += [DetailedObservation("S1", "2025-10-10", {"VV_median": -10, "VH_median": -20, "VV_minus_VH_median": 10, "valid_pixel_count": 20, "orbit_pass": "DESCENDING", "orbit_number": 92})]
    result = estimate_stage(observations)
    assert result["peak_confirmed"] is False
    assert result["stage"] in {"Vegetative / Tillering", "Establishment / Transplanting"}
    assert "true peak not confirmed" in result["maximum_interpretation"]
