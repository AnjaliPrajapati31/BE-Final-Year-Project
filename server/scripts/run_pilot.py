from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.sickle.runtime import SickleRuntime
from app.services.sickle.crop import summarize_crop, validate_crop_inputs
from app.services.sickle.providers.local_fixture import LocalFixtureProvider
from app.services.sickle.stage import estimate_stage
from app.services.sickle.stress import estimate_stress


def main() -> None:
    fixture = LocalFixtureProvider(Path("tests/fixtures/sickle/pilot_001"))
    readiness = fixture.readiness()
    if not readiness["ready"]:
        raise SystemExit(f"PILOT_001 scientific gate blocked; missing: {', '.join(readiness['missing'])}")
    inputs = fixture.crop_inputs()
    validate_crop_inputs(inputs)
    runtime = SickleRuntime.load(Path("ml_models/sickle/checkpoint_best.pt"), "cpu", 1)
    crop = summarize_crop(runtime.infer(inputs.s1, inputs.s1_dates, inputs.s2, inputs.s2_dates), inputs.field_mask, inputs)
    stage = estimate_stage(fixture.detailed_series())
    stress = estimate_stress(fixture.detailed_series(), stage, crop)
    checks = [
        crop["class_label"] == "Paddy",
        abs(crop["paddy_probability"] - 0.7029250264167786) <= 1e-4,
        crop["paddy_pixel_fraction"] == 1.0,
        crop["field_pixel_count"] == 87,
        inputs.s1.shape == (5, 2, 32, 32),
        inputs.s2.shape == (3, 12, 32, 32),
        stage["stage"] == "Vegetative / Tillering",
        stage["cycle_start"] == "2025-10-11",
        stage["latest_observation"] == "2025-10-31",
        stage["current_cycle_count"] == 2,
        stage["peak_confirmed"] is False,
        stage["selected_s1_orbit_pass"] == "DESCENDING",
        stage["selected_s1_orbit_number"] == 92,
        stress["status"] == "completed",
        stress["stress_risk"] == "No stress evidence",
        abs(stress["stress_score"] - 0.05) <= 1e-6,
        stress["latest_observation_date"] == "2025-10-31",
    ]
    if not all(checks):
        raise SystemExit(f"PILOT_001 scientific parity gate FAILED\ncrop={crop}\nstage={stage}\nstress={stress}")
    print("PILOT_001 scientific parity gate PASSED")


if __name__ == "__main__":
    main()
