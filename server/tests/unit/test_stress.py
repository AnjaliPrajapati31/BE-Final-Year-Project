import pytest

from app.services.sickle.contracts import DetailedObservation
from app.services.sickle.stress import estimate_stress

pytestmark = pytest.mark.unit


def stage(label="Vegetative / Tillering"):
    return {
        "status": "completed",
        "stage": label,
        "evidence": "Moderate provisional evidence",
        "cycle_start": "2025-06-01",
        "selected_s1_orbit_pass": "DESCENDING",
        "selected_s1_orbit_number": 92,
    }


def s2(day, ndvi, ndmi, ndwi=None, cloud=10):
    return DetailedObservation("S2", f"2025-06-{day:02d}", {
        "NDVI_median": ndvi, "NDMI_median": ndmi,
        "NDWI_median": (ndmi - 0.2) if ndwi is None and isinstance(ndmi, (int, float)) else ndwi,
        "NDVI_count": 20, "scene_cloud_percentage": cloud,
    })


def s1(day, vv, vh):
    return DetailedObservation("S1", f"2025-06-{day:02d}", {
        "VV_median": vv, "VH_median": vh, "VV_count": 20,
        "orbitProperties_pass": "DESCENDING", "relativeOrbitNumber_start": 92,
    })


def test_non_paddy_and_maturity_are_explicitly_skipped():
    non_paddy = estimate_stress([], stage(), {"class_label": "Non-Paddy"})
    maturity = estimate_stress([], stage("Maturity / Harvest"), {"class_label": "Paddy"})
    assert non_paddy["status"] == "skipped"
    assert non_paddy["reason_code"] == "NON_PADDY_STRESS_SKIPPED"
    assert maturity["status"] == "skipped"


def test_missing_stage_or_optical_data_is_insufficient():
    unavailable = estimate_stress([], {"status": "insufficient_data"}, {"class_label": "Paddy"})
    missing_s2 = estimate_stress([], stage(), {"class_label": "Paddy"})
    assert unavailable["reason_code"] == "STAGE_UNAVAILABLE_FOR_STRESS"
    assert missing_s2["reason_code"] == "INSUFFICIENT_S2_FOR_STRESS"


def test_latest_severely_cloudy_observation_fails_quality_gate():
    result = estimate_stress(
        [s2(1, 0.5, 0.3), s2(11, 0.48, 0.28, cloud=85)],
        stage(), {"class_label": "Paddy"},
    )
    assert result["status"] == "insufficient_data"
    assert result["reason_code"] == "LATEST_OPTICAL_CLOUD_CONTAMINATED"


def test_optical_only_result_completes_and_reports_missing_radar():
    result = estimate_stress(
        [s2(1, 0.4, 0.2), s2(11, 0.45, 0.22), s2(21, 0.5, 0.24)],
        stage(), {"class_label": "Paddy"},
    )
    assert result["status"] == "completed"
    assert any("No S1 radar" in item for item in result["counter_evidence"])


def test_persistent_optical_anomaly_and_radar_add_evidence():
    observations = [
        s2(1, 0.70, 0.50), s2(6, 0.68, 0.51), s2(11, 0.65, 0.49),
        s2(16, 0.52, 0.20), s2(21, 0.40, 0.10),
        s1(1, -10.0, -16.0), s1(11, -10.2, -16.2), s1(21, -14.0, -20.0),
    ]
    result = estimate_stress(observations, stage(), {"class_label": "Paddy"})
    assert result["status"] == "completed"
    assert result["persistence_observations"] >= 2
    assert result["stress_score"] >= 0.4
    assert any("Radar" in item for item in result["evidence"])


def test_malformed_optical_values_do_not_produce_a_score():
    result = estimate_stress(
        [s2(1, "bad", None), s2(11, 4.0, -3.0)],
        stage(), {"class_label": "Paddy"},
    )
    assert result["status"] == "insufficient_data"
    assert result["stress_score"] is None
