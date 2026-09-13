from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.pool import Database
from app.db.repositories import AnalysisRepository
from app.services.sickle.geometry import load_roi
from app.ml.sickle.runtime import EXPECTED_PARAMETER_COUNT, SickleRuntime
from app.services.sickle.providers.earth_engine import EarthEngineProvider
from app.services.weather.earth_engine import EarthEngineWeatherProvider


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
    checks["database"] = False
    checks["database_schema"] = False
    if settings.DATABASE_URL:
        database = Database(
            settings.DATABASE_URL, settings.DATABASE_POOL_MIN_SIZE,
            settings.DATABASE_POOL_MAX_SIZE, settings.DATABASE_CONNECT_TIMEOUT_SECONDS,
        )
        try:
            database.open()
            database.check()
            checks["database"] = True
            checks["database_schema"] = AnalysisRepository(database.pool, settings.CAUVERY_ROI_CODE).schema_readiness()["ready"]
        finally:
            database.close()
    provider = EarthEngineProvider(
        settings.EARTH_ENGINE_PROJECT_ID or "", settings.path(settings.EARTH_ENGINE_CACHE_ROOT),
        settings.EARTH_ENGINE_CACHE_TTL_SECONDS, settings.EARTH_ENGINE_MAX_RETRIES,
        settings.EARTH_ENGINE_REQUEST_TIMEOUT_SECONDS, settings.EARTH_ENGINE_ENABLED,
        settings.EARTH_ENGINE_AUTH_MODE, settings.EARTH_ENGINE_ENDPOINT,
        settings.GOOGLE_APPLICATION_CREDENTIALS, settings.CAUVERY_ROI_VERSION,
    )
    provider.initialize()
    checks["satellite_provider"] = provider.readiness()["ready"]
    weather = EarthEngineWeatherProvider(provider)
    checks["historical_weather_provider"] = weather.readiness()["ready"]
    checks["forecast_weather_provider"] = weather.readiness()["ready"]
    artifact_root = settings.path(settings.SICKLE_ARTIFACT_ROOT)
    if settings.SICKLE_ARTIFACTS_ENABLED:
        artifact_root.mkdir(parents=True, exist_ok=True)
        checks["artifact_storage"] = artifact_root.is_dir()
    else:
        checks["artifact_storage"] = True
    print(json.dumps(checks, indent=2))
    if not all(checks.values()):
        raise SystemExit("Production readiness FAILED")


if __name__ == "__main__":
    main()
