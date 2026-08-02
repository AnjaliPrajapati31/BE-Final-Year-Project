import pytest

from app.config import settings
from app.services.sickle.providers.earth_engine import EarthEngineProvider

pytestmark = pytest.mark.gee_live


def test_earth_engine_adc_initializes(tmp_path):
    project = settings.EARTH_ENGINE_PROJECT_ID
    if not project:
        pytest.skip("EARTH_ENGINE_PROJECT_ID is not configured")
    provider = EarthEngineProvider(project, tmp_path, 60, 0)
    provider.initialize()
    assert provider.readiness()["ready"] is True
