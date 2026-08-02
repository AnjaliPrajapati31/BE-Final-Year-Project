from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    APP_NAME: str = "AI Agriculture API"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"
    DATABASE_URL: str | None = None
    DATABASE_POOL_MIN_SIZE: int = 1
    DATABASE_POOL_MAX_SIZE: int = 5
    DATABASE_CONNECT_TIMEOUT_SECONDS: int = 10
    EARTH_ENGINE_ENABLED: bool = True
    EARTH_ENGINE_PROJECT_ID: str | None = None
    EARTH_ENGINE_AUTH_MODE: str = "adc"
    EARTH_ENGINE_ENDPOINT: str = "https://earthengine.googleapis.com"
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    EARTH_ENGINE_REQUEST_TIMEOUT_SECONDS: int = 120
    EARTH_ENGINE_MAX_RETRIES: int = 2
    EARTH_ENGINE_CACHE_ROOT: str = "cache/earth_engine"
    EARTH_ENGINE_CACHE_TTL_SECONDS: int = 86400
    SICKLE_CHECKPOINT_PATH: str = "ml_models/sickle/checkpoint_best.pt"
    SICKLE_DEVICE: str = "auto"
    SICKLE_MAX_CONCURRENT_INFERENCES: int = 1
    CAUVERY_ROI_CODE: str = "cauvery_delta_pilot"
    CAUVERY_ROI_VERSION: int = 2
    CAUVERY_ROI_PATH: str = "resources/cauvery/v2/cauvery_delta_pilot_v2.geojson"
    FIELD_MIN_AREA_M2: float = 100
    FIELD_MAX_AREA_M2: float = 78400
    FIELD_MAX_WIDTH_M: float = 280
    FIELD_MAX_HEIGHT_M: float = 280
    FIELD_MAX_VERTICES: int = 10000
    CROP_ZERO_FRACTION_LIMIT: float = 0.25
    CROP_MIN_S1_OBSERVATIONS: int = 1
    CROP_MIN_S2_OBSERVATIONS: int = 1
    SICKLE_ARTIFACTS_ENABLED: bool = False
    SICKLE_ARTIFACT_ROOT: str = "artifacts/sickle"

    def path(self, value: str) -> Path:
        candidate = Path(value)
        return candidate if candidate.is_absolute() else BASE_DIR / candidate

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
