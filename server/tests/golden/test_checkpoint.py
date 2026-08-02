from pathlib import Path

import pytest

from app.ml.sickle.runtime import EXPECTED_PARAMETER_COUNT, SickleRuntime
from app.services.sickle.crop import summarize_crop, validate_crop_inputs
from app.services.sickle.providers.local_fixture import LocalFixtureProvider
from app.services.sickle.stage import estimate_stage

pytestmark = pytest.mark.golden


def test_checkpoint_loads_strictly_with_exact_parameter_count():
    runtime = SickleRuntime.load(Path("ml_models/sickle/checkpoint_best.pt"), "cpu", 1)
    assert sum(parameter.numel() for parameter in runtime.model.parameters()) == EXPECTED_PARAMETER_COUNT


def test_pilot_crop_probability_matches_original_checkpoint():
    provider = LocalFixtureProvider(Path("tests/fixtures/sickle/pilot_001"))
    inputs = provider.crop_inputs()
    validate_crop_inputs(inputs)
    runtime = SickleRuntime.load(Path("ml_models/sickle/checkpoint_best.pt"), "cpu", 1)
    crop = summarize_crop(runtime.infer(inputs.s1, inputs.s1_dates, inputs.s2, inputs.s2_dates), inputs.field_mask, inputs)
    assert inputs.s1.shape == (5, 2, 32, 32)
    assert inputs.s2.shape == (3, 12, 32, 32)
    assert crop["class_label"] == "Paddy"
    assert crop["paddy_probability"] == pytest.approx(0.7029250264167786, abs=1e-4)
    assert crop["paddy_pixel_fraction"] == 1.0
    assert crop["field_pixel_count"] == 87


def test_raw_pilot_timeseries_matches_corrected_stage():
    provider = LocalFixtureProvider(Path("tests/fixtures/sickle/pilot_001"))
    observations = provider.detailed_series()
    result = estimate_stage(observations)
    assert result["stage"] == "Vegetative / Tillering"
    assert result["evidence"] == "Low provisional evidence"
    assert result["cycle_start"] == "2025-10-11"
    assert result["latest_observation"] == "2025-10-31"
    assert result["current_cycle_count"] == 2
    assert result["peak_confirmed"] is False
    assert result["selected_s1_orbit_pass"] == "DESCENDING"
    assert result["selected_s1_orbit_number"] == 92
    assert result["clean_s1_observation_count"] == 12
    assert result["clean_s2_observation_count"] == 15
