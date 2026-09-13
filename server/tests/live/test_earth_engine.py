import json
from datetime import date
from pathlib import Path

import pytest

from app.config import settings
from app.services.sickle.providers.earth_engine import EarthEngineProvider
from app.services.sickle.geometry import validate_geometry
from app.services.weather.earth_engine import EarthEngineWeatherProvider

pytestmark = pytest.mark.gee_live


def test_earth_engine_adc_initializes(tmp_path):
    project = settings.EARTH_ENGINE_PROJECT_ID
    if not project:
        pytest.skip("EARTH_ENGINE_PROJECT_ID is not configured")
    provider = EarthEngineProvider(project, tmp_path, 60, 0)
    provider.initialize()
    assert provider.readiness()["ready"] is True


def test_historical_weather_returns_fao56_daily_row(tmp_path):
    project = settings.EARTH_ENGINE_PROJECT_ID
    if not project:
        pytest.skip("EARTH_ENGINE_PROJECT_ID is not configured")
    payload = json.loads(Path(__file__).parents[2].joinpath("tests/fixtures/sickle/pilot_001/pilot_001.geojson").read_text())
    geometry = validate_geometry(
        payload["features"][0]["geometry"], max_vertices=10000, min_area_m2=100, max_area_m2=78400,
        max_width_m=280, max_height_m=280, roi=None,
    )
    provider = EarthEngineProvider(project, tmp_path, 60, 0)
    provider.initialize()
    rows = EarthEngineWeatherProvider(provider).historical(
        geometry, date(2025, 7, 1), date(2025, 7, 1), "weather-live-test"
    )
    assert len(rows) == 1
    assert rows[0].rainfall_mm >= 0
    assert rows[0].et0_mm >= 0


def test_gfs_forecast_uses_deduplicated_six_hour_accumulations(tmp_path):
    project = settings.EARTH_ENGINE_PROJECT_ID
    if not project:
        pytest.skip("EARTH_ENGINE_PROJECT_ID is not configured")
    payload = json.loads(Path(__file__).parents[2].joinpath("tests/fixtures/sickle/pilot_001/pilot_001.geojson").read_text())
    geometry = validate_geometry(
        payload["features"][0]["geometry"], max_vertices=10000, min_area_m2=100,
        max_area_m2=78400, max_width_m=280, max_height_m=280, roi=None,
    )
    provider = EarthEngineProvider(project, tmp_path, 60, 0)
    provider.initialize()
    rows = EarthEngineWeatherProvider(provider).forecast(geometry, date.today(), 3, "forecast-live-test")
    assert 1 <= len(rows) <= 3
    assert len({row.date for row in rows}) == len(rows)
    assert all(row.rainfall_mm >= 0 and row.et0_mm >= 0 for row in rows)
    assert all("6_hour_steps" in row.quality for row in rows)
