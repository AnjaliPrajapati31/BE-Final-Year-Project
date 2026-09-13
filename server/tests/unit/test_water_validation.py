import pytest

from app.services.water.validation import build_validation_report, paired_error_metrics

pytestmark = pytest.mark.unit


def test_error_metrics_are_paired_and_reproducible():
    rows = [
        {"estimated": 3, "observed": 2},
        {"estimated": 4, "observed": 6},
        {"estimated": None, "observed": 10},
    ]
    result = paired_error_metrics(rows, "estimated", "observed")
    assert result == {"sample_count": 2, "bias": -0.5, "mae": 1.5, "rmse": pytest.approx(1.58113883)}


def test_empty_validation_data_never_publishes_accuracy():
    result = build_validation_report([])
    assert result["status"] == "insufficient_validation_data"
    assert result["water_deficit_accuracy_publishable"] is False
    assert not any(result["requirements"].values())


def test_complete_five_field_fixture_opens_validation_gate():
    fields = []
    for index in range(5):
        fields.append({
            "field_id": f"FIELD_{index}", "known_crop_label": "Paddy",
            "transplanting_date": "2025-06-01", "soil_description": "clay loam",
            "has_dry_down_event": index == 0,
            "has_rainfall_or_irrigation_refill_event": index == 1,
            "observations": [{
                "estimated_rainfall_mm": 5, "observed_rainfall_mm": 5,
                "calculated_et0_mm": 4, "reference_et0_mm": 4,
                "estimated_ponded_water_mm": 20, "observed_ponded_water_mm": 20,
                "estimated_root_depletion_mm": None, "observed_root_depletion_mm": None,
                "conservation_residual_mm": 0,
            }],
        })
    result = build_validation_report(fields)
    assert result["status"] == "validation_complete"
    assert result["water_deficit_accuracy_publishable"] is True


def test_nonfinite_measurements_are_rejected():
    with pytest.raises(ValueError, match="finite"):
        paired_error_metrics([{"estimated": float("nan"), "observed": 1}], "estimated", "observed")
