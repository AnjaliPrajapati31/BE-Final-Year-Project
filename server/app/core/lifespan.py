from __future__ import annotations

import logging
import json
from contextlib import asynccontextmanager

from app.config import settings
from app.db.pool import Database
from app.db.repositories import AnalysisRepository
from app.ml.sickle.runtime import SickleRuntime
from app.services.sickle.analysis import AnalysisService
from app.services.sickle.artifacts import ArtifactWriter
from app.services.sickle.geometry import load_roi
from app.services.sickle.providers.earth_engine import EarthEngineProvider
from app.services.weather.earth_engine import EarthEngineWeatherProvider
from app.services.explanation import OpenAIExplanationProvider

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    app.state.dependencies = {}
    app.state.database = None
    app.state.repository = None
    app.state.roi = None
    app.state.crop_runtime = None
    app.state.provider = None
    app.state.analysis_service = None
    app.state.explanation_provider = OpenAIExplanationProvider(
        settings.AI_EXPLANATION_API_KEY if settings.AI_EXPLANATION_ENABLED else None,
        settings.AI_EXPLANATION_MODEL if settings.AI_EXPLANATION_ENABLED else None,
        settings.AI_EXPLANATION_ENDPOINT,
        settings.AI_EXPLANATION_TIMEOUT_SECONDS,
    )
    app.state.dependencies["ai_explanation"] = {
        "ready": app.state.explanation_provider.enabled,
        "required": False,
        "provider": "openai-responses",
        "model": settings.AI_EXPLANATION_MODEL,
    }
    app.state.dependencies["database_schema"] = {"ready": False, "error": "Database schema has not been checked."}
    roi_checksum = None
    try:
        app.state.roi, roi_checksum = load_roi(settings.path(settings.CAUVERY_ROI_PATH))
        manifest_path = settings.path(settings.CAUVERY_ROI_PATH).with_name("manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "approved" or manifest.get("sha256") != roi_checksum or manifest.get("version") != settings.CAUVERY_ROI_VERSION:
            raise RuntimeError("Cauvery ROI manifest is not approved or does not match the resource")
        app.state.dependencies["roi_resource"] = {"ready": True, "sha256": roi_checksum, "version": settings.CAUVERY_ROI_VERSION}
    except Exception as exc:
        app.state.dependencies["roi_resource"] = {"ready": False, "error": str(exc)}
        logger.warning("Cauvery ROI resource is not ready")
    if settings.DATABASE_URL:
        try:
            database = Database(settings.DATABASE_URL, settings.DATABASE_POOL_MIN_SIZE, settings.DATABASE_POOL_MAX_SIZE, settings.DATABASE_CONNECT_TIMEOUT_SECONDS)
            database.open()
            details = database.check()
            repository = AnalysisRepository(database.pool, settings.CAUVERY_ROI_CODE)
            schema_details = repository.schema_readiness()
            app.state.dependencies["database_schema"] = schema_details
            if not schema_details["ready"]:
                raise RuntimeError("Required database migrations or tables are missing")
            active_roi = repository.active_roi()
            if not active_roi:
                raise RuntimeError("No active Cauvery ROI exists in PostGIS")
            if roi_checksum and active_roi["source_checksum"] != roi_checksum:
                raise RuntimeError("ROI resource and PostGIS checksums differ")
            app.state.database, app.state.repository = database, repository
            app.state.dependencies["database"] = {"ready": True, **details}
        except Exception:
            if "database" in locals():
                database.close()
            app.state.dependencies["database"] = {"ready": False, "error": "Database, PostGIS, or seeded ROI is unavailable."}
            logger.exception("Database readiness failed")
    else:
        app.state.dependencies["database"] = {"ready": False, "error": "DATABASE_URL is not configured."}
    try:
        runtime = SickleRuntime.load(settings.path(settings.SICKLE_CHECKPOINT_PATH), settings.SICKLE_DEVICE, settings.SICKLE_MAX_CONCURRENT_INFERENCES)
        app.state.crop_runtime = runtime
        app.state.dependencies["sickle_model"] = {"ready": True, "device": str(runtime.device), "checkpoint_sha256": runtime.checkpoint_sha256}
    except Exception:
        app.state.dependencies["sickle_model"] = {"ready": False, "error": "SICKLE model failed strict startup validation."}
        logger.exception("SICKLE model readiness failed")
    provider = EarthEngineProvider(settings.EARTH_ENGINE_PROJECT_ID or "", settings.path(settings.EARTH_ENGINE_CACHE_ROOT), settings.EARTH_ENGINE_CACHE_TTL_SECONDS, settings.EARTH_ENGINE_MAX_RETRIES, settings.EARTH_ENGINE_REQUEST_TIMEOUT_SECONDS, settings.EARTH_ENGINE_ENABLED, settings.EARTH_ENGINE_AUTH_MODE, settings.EARTH_ENGINE_ENDPOINT, settings.GOOGLE_APPLICATION_CREDENTIALS, settings.CAUVERY_ROI_VERSION)
    provider.initialize()
    app.state.provider = provider
    app.state.dependencies["earth_engine"] = provider.readiness()
    weather_provider = EarthEngineWeatherProvider(provider)
    app.state.weather_provider = weather_provider
    app.state.dependencies["historical_weather"] = weather_provider.readiness()
    app.state.dependencies["forecast_weather"] = weather_provider.readiness()
    artifact_writer = ArtifactWriter(settings.path(settings.SICKLE_ARTIFACT_ROOT), settings.SICKLE_ARTIFACTS_ENABLED)
    try:
        if settings.SICKLE_ARTIFACTS_ENABLED:
            artifact_writer.root.mkdir(parents=True, exist_ok=True)
        app.state.dependencies["artifacts"] = {"ready": True, "enabled": settings.SICKLE_ARTIFACTS_ENABLED}
    except OSError:
        app.state.dependencies["artifacts"] = {"ready": False, "enabled": True, "error": "Artifact root is not writable."}
    required = (app.state.roi, app.state.repository, app.state.crop_runtime)
    if all(item is not None for item in required) and provider.readiness()["ready"] and app.state.dependencies["artifacts"]["ready"]:
        app.state.analysis_service = AnalysisService(settings, app.state.roi, app.state.repository, provider, app.state.crop_runtime, artifact_writer, weather_provider)
    try:
        yield
    finally:
        if app.state.database is not None:
            app.state.database.close()
