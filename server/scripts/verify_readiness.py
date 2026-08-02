from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services.sickle.geometry import load_roi
from app.ml.sickle.runtime import EXPECTED_PARAMETER_COUNT, SickleRuntime


def main() -> None:
    checks = {}
    roi_path = settings.path(settings.CAUVERY_ROI_PATH)
    checks["approved_roi_resource"] = roi_path.is_file()
    manifest = json.loads((roi_path.parent / "manifest.json").read_text(encoding="utf-8"))
    _, roi_checksum = load_roi(roi_path)
    checks["approved_roi_manifest"] = (
        manifest.get("status") == "approved"
        and manifest.get("version") == settings.CAUVERY_ROI_VERSION
        and manifest.get("sha256") == roi_checksum
    )
    runtime = SickleRuntime.load(settings.path(settings.SICKLE_CHECKPOINT_PATH), "cpu", 1)
    checks["strict_checkpoint"] = sum(parameter.numel() for parameter in runtime.model.parameters()) == EXPECTED_PARAMETER_COUNT
    fixture_root = Path("tests/fixtures/sickle/pilot_001")
    checks["pilot_crop_fixture"] = (fixture_root / "pilot_001_sickle_input.npz").is_file()
    checks["pilot_detailed_fixtures"] = all((fixture_root / name).is_file() for name in ("pilot_001_s1_detailed.csv", "pilot_001_s2_detailed.csv"))
    checks["database_url"] = bool(settings.DATABASE_URL)
    checks["earth_engine_project"] = bool(settings.EARTH_ENGINE_PROJECT_ID)
    print(json.dumps(checks, indent=2))
    if not all(checks.values()):
        raise SystemExit("Production readiness FAILED")


if __name__ == "__main__":
    main()
