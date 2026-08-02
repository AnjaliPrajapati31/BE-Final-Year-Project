from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.ml.sickle.runtime import SickleRuntime
from app.services.sickle.crop import summarize_crop, validate_crop_inputs
from app.services.sickle.geometry import load_roi, validate_geometry
from app.services.sickle.providers.earth_engine import EarthEngineProvider
from app.services.sickle.providers.local_fixture import LocalFixtureProvider
from app.services.sickle.stage import estimate_stage


def main() -> None:
    fixture_root = Path("tests/fixtures/sickle/pilot_001")
    payload = json.loads((fixture_root / "pilot_001.geojson").read_text(encoding="utf-8"))
    geometry_payload = payload["features"][0]["geometry"]
    roi, _ = load_roi(settings.path(settings.CAUVERY_ROI_PATH))
    geometry = validate_geometry(
        geometry_payload,
        max_vertices=settings.FIELD_MAX_VERTICES,
        min_area_m2=settings.FIELD_MIN_AREA_M2,
        max_area_m2=settings.FIELD_MAX_AREA_M2,
        max_width_m=settings.FIELD_MAX_WIDTH_M,
        max_height_m=settings.FIELD_MAX_HEIGHT_M,
        roi=roi,
    )
    provider = EarthEngineProvider(
        settings.EARTH_ENGINE_PROJECT_ID or "",
        settings.path(settings.EARTH_ENGINE_CACHE_ROOT),
        settings.EARTH_ENGINE_CACHE_TTL_SECONDS,
        settings.EARTH_ENGINE_MAX_RETRIES,
        settings.EARTH_ENGINE_REQUEST_TIMEOUT_SECONDS,
        settings.EARTH_ENGINE_ENABLED,
        settings.EARTH_ENGINE_AUTH_MODE,
        settings.EARTH_ENGINE_ENDPOINT,
        settings.GOOGLE_APPLICATION_CREDENTIALS,
        settings.CAUVERY_ROI_VERSION,
    )
    provider.initialize()
    if not provider.readiness()["ready"]:
        raise SystemExit("Earth Engine initialization failed; verify ADC and project access.")

    live = provider.crop_inputs(geometry, 2025, "pilot-001-live-characterization")
    golden = LocalFixtureProvider(fixture_root).crop_inputs()
    validate_crop_inputs(live)
    runtime = SickleRuntime.load(settings.path(settings.SICKLE_CHECKPOINT_PATH), "cpu", 1)
    live_crop = summarize_crop(runtime.infer(live.s1, live.s1_dates, live.s2, live.s2_dates), live.field_mask, live)
    golden_crop = summarize_crop(runtime.infer(golden.s1, golden.s1_dates, golden.s2, golden.s2_dates), golden.field_mask, golden)
    stage = estimate_stage(provider.detailed_series(geometry, 2025, "pilot-001-stage-characterization"))

    report = {
        "grid_equal": live.grid == golden.grid,
        "field_pixels": int(live.field_mask.sum()),
        "live_s1_shape": list(live.s1.shape),
        "live_s2_shape": list(live.s2.shape),
        "live_s1_months": live.s1_months,
        "live_s2_months": live.s2_months,
        "golden_s1_months": golden.s1_months,
        "golden_s2_months": golden.s2_months,
        "s1_arrays_equal": live.s1.shape == golden.s1.shape and bool(np.allclose(live.s1, golden.s1)),
        "s2_arrays_equal": live.s2.shape == golden.s2.shape and bool(np.allclose(live.s2, golden.s2)),
        "live_paddy_probability": live_crop["paddy_probability"],
        "golden_paddy_probability": golden_crop["paddy_probability"],
        "probability_delta": abs(live_crop["paddy_probability"] - golden_crop["paddy_probability"]),
        "live_crop": live_crop["class_label"],
        "live_stage": stage.get("stage"),
        "live_stage_reason": stage.get("reason_code"),
        "provider_cached": live.cached,
    }
    print(json.dumps(report, indent=2))
    if report["probability_delta"] > 1e-4:
        raise SystemExit("Live PILOT_001 parity gate FAILED: monthly export reconstruction differs from the golden input.")
    print("Live PILOT_001 parity gate PASSED")


if __name__ == "__main__":
    main()
