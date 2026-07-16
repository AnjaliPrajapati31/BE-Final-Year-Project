from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml_models"


class Settings(BaseSettings):
    APP_NAME: str = "Crop API"


settings = Settings()