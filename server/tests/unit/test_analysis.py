from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
from shapely.geometry import box

from app.core.exceptions import DomainError
from app.schemas.field_analysis import FieldAnalysisRequest
from app.services.sickle.analysis import AnalysisService
from app.services.sickle.contracts import CropInputs, Grid
from app.services.sickle.providers.local_fixture import LocalFixtureProvider
from app.services.water.contracts import DailyWeather

pytestmark = pytest.mark.unit


class Repository:
    def __init__(self):
        self.created = 0
        self.statuses = []
        self.status_payloads = []
        self.result_payloads = {}

    def verify_roi(self, field, patch): return uuid4()
    def create_revision_and_run(self, *args): self.created += 1
    def set_status(self, request_id, status, **kwargs):
        self.statuses.append(status)
        self.status_payloads.append((status, kwargs))
    def save_crop(self, *args): pass
    def save_stage(self, *args): pass
    def save_crop_quality(self, *args): pass
    def set_provider_cached(self, *args): pass
    def save_artifact(self, *args): pass
    def save_observations(self, *args): pass
    def save_stress(self, *args): pass
    def save_module_run(self, request_id, module, result): pass
    def get_water_profile(self, field_id): return None
    def irrigation_depths(self, field_id, start, end): return []
    def save_weather(self, *args): pass
    def save_water_balance(self, request_id, result): self.balance = result
    def save_advisory(self, request_id, result): self.advisory = result
    def save_result_payload(self, request_id, result_type, payload): self.result_payloads[result_type] = payload


class Provider:
    name = "fake_earth_engine"
    live_data = True

    def __init__(self): self.calls = 0
    def crop_inputs(self, *args):
        self.calls += 1
        mask = np.zeros((32, 32), bool)
        interior = np.argwhere(np.ones((30, 30), dtype=bool)) + 1
        for row, column in interior[:args[0].field_pixel_count]:
            mask[row, column] = True
        return CropInputs(np.ones((1,2,32,32),np.float32),np.array([15]),["June"],np.ones((1,12,32,32),np.float32),np.array([15]),["June"],mask,Grid("EPSG:32644",(10,0,0,0,-10,320)),[],self.name,True)


class Runtime:
    model_name = "test"; checkpoint_sha256 = "a" * 64
    def infer(self, *args):
        probabilities = np.empty((2,32,32),np.float32); probabilities[0]=0.1; probabilities[1]=0.9
        return probabilities


class PaddyRuntime(Runtime):
    def infer(self, *args):
        probabilities = np.empty((2,32,32),np.float32); probabilities[0]=0.9; probabilities[1]=0.1
        return probabilities


class PaddyProvider(Provider):
    def detailed_series(self, *args):
        return LocalFixtureProvider(Path("tests/fixtures/sickle/pilot_001")).detailed_series()


class WeatherProvider:
    def historical(self, geometry, start, end, request_id):
        return [DailyWeather(start + timedelta(days=index), 2, 4, source="weather_fixture") for index in range((end - start).days + 1)]
    def forecast(self, *args):
        return []


class MissingStageProvider(Provider):
    def detailed_series(self, *args):
        raise DomainError("INSUFFICIENT_SENTINEL2", "No usable optical observations.")


class FailingWeatherProvider:
    def historical(self, *args):
        raise DomainError("HISTORICAL_WEATHER_UNAVAILABLE", "Historical weather failed.", 503)


class StaleWeatherProvider(WeatherProvider):
    def historical(self, geometry, start, end, request_id):
        return super().historical(geometry, start, end - timedelta(days=1), request_id)


class InvalidProfileRepository(Repository):
    def get_water_profile(self, field_id):
        return {"source": "user", "overrides": {"field_capacity": 0.1, "wilting_point": 0.2}}


class FailingCreateRepository(Repository):
    def create_revision_and_run(self, *args):
        raise RuntimeError("database unavailable")


class Artifacts: pass


class FailingArtifacts:
    def write_analysis(self, *args):
        raise DomainError("ARTIFACT_WRITE_FAILED", "Could not create the crop GeoTIFF artifact.", 500)


def settings():
    return SimpleNamespace(FIELD_MAX_VERTICES=10000,FIELD_MIN_AREA_M2=100,FIELD_MAX_AREA_M2=78400,FIELD_MAX_WIDTH_M=280,FIELD_MAX_HEIGHT_M=280,CAUVERY_ROI_VERSION=1)


def command_at(lon, lat):
    return FieldAnalysisRequest.model_validate({"field_id":"FIELD_001","geometry":{"type":"Polygon","coordinates":[[[lon,lat],[lon+0.001,lat],[lon+0.001,lat+0.001],[lon,lat+0.001],[lon,lat]]]},"year":2025})


def command_at_with_artifacts(lon, lat):
    return FieldAnalysisRequest.model_validate({"field_id":"FIELD_001","geometry":{"type":"Polygon","coordinates":[[[lon,lat],[lon+0.001,lat],[lon+0.001,lat+0.001],[lon,lat+0.001],[lon,lat]]]},"year":2025,"generate_artifacts":True})


def test_non_paddy_completes_without_stage_provider_call():
    repository, provider = Repository(), Provider()
    service = AnalysisService(settings(), box(78,10,80,12), repository, provider, Runtime(), Artifacts())
    result = service.analyze(command_at(79,11))
    assert result["crop"]["class_label"] == "Non-Paddy"
    assert result["growth_stage"]["reason_code"] == "NON_PADDY_STAGE_SKIPPED"
    assert repository.created == 1 and provider.calls == 1
    assert result["modules"]["growth_stage"]["status"] == "skipped"
    assert result["modules"]["moisture_stress"]["status"] == "skipped"
    assert result["modules"]["weather"]["status"] == "skipped"
    assert result["modules"]["water_balance"]["status"] == "skipped"
    assert result["modules"]["irrigation_advisory"]["status"] == "skipped"


def test_outside_roi_never_creates_or_calls_provider():
    repository, provider = Repository(), Provider()
    service = AnalysisService(settings(), box(78,10,80,12), repository, provider, Runtime(), Artifacts())
    with pytest.raises(DomainError) as error:
        service.analyze(command_at(82,15))
    assert error.value.code == "OUTSIDE_SUPPORTED_ROI"
    assert repository.created == 0 and provider.calls == 0


def test_artifact_failure_marks_analysis_partial_without_masking_crop_result():
    repository, provider = Repository(), Provider()
    service = AnalysisService(settings(), box(78,10,80,12), repository, provider, Runtime(), FailingArtifacts())
    result = service.analyze(command_at_with_artifacts(79,11))
    assert result["crop"]["class_label"] == "Non-Paddy"
    assert result["status"] == "partial"
    assert "Could not create the crop GeoTIFF artifact." in result["warnings"]
    assert repository.statuses[-1] == "partial"


def test_paddy_runs_weather_balance_and_current_state_advisory_independently_of_stress():
    repository, provider = Repository(), PaddyProvider()
    service = AnalysisService(
        settings(), box(78,10,80,12), repository, provider, PaddyRuntime(), Artifacts(), WeatherProvider()
    )
    command = command_at(79,11).model_copy(update={"transplanting_date_hint": date(2025, 10, 11)})
    result = service.analyze(command)
    assert result["crop"]["class_label"] == "Paddy"
    assert result["modules"]["weather"]["status"] == "completed"
    assert result["modules"]["water_balance"]["status"] == "completed"
    assert result["modules"]["irrigation_advisory"]["status"] == "completed"
    assert result["water_balance"]["water_deficit_mm"] >= 0
    assert result["irrigation_advisory"]["action"] in {"irrigate_now", "monitor", "no_irrigation_required"}
    assert repository.result_payloads["crop"] == result["crop"]
    assert repository.result_payloads["growth_stage"] == result["growth_stage"]
    assert repository.result_payloads["moisture_stress"] == result["moisture_stress"]
    assert repository.result_payloads["water_balance"] == result["water_balance"]
    assert repository.result_payloads["irrigation_advisory"] == result["irrigation_advisory"]
    assert repository.result_payloads["charts"] == result["charts"]


def test_missing_stage_evidence_skips_weather_and_preserves_crop():
    service = AnalysisService(settings(), box(78,10,80,12), Repository(), MissingStageProvider(), PaddyRuntime(), Artifacts(), WeatherProvider())
    result = service.analyze(command_at(79,11))
    assert result["crop"]["class_label"] == "Paddy"
    assert result["modules"]["growth_stage"]["status"] == "insufficient_data"
    assert result["modules"]["weather"]["status"] == "skipped"
    assert result["modules"]["water_balance"]["status"] == "insufficient_data"
    assert result["modules"]["irrigation_advisory"]["status"] == "skipped"


def test_weather_failure_does_not_erase_crop_stage_or_stress():
    service = AnalysisService(settings(), box(78,10,80,12), Repository(), PaddyProvider(), PaddyRuntime(), Artifacts(), FailingWeatherProvider())
    result = service.analyze(command_at(79,11))
    assert result["crop"] and result["growth_stage"] and result["moisture_stress"]
    assert result["modules"]["weather"]["status"] == "failed"
    assert result["modules"]["water_balance"]["status"] == "insufficient_data"
    assert result["modules"]["irrigation_advisory"]["status"] == "skipped"


def test_stale_historical_state_calculates_balance_but_blocks_advisory():
    service = AnalysisService(settings(), box(78,10,80,12), Repository(), PaddyProvider(), PaddyRuntime(), Artifacts(), StaleWeatherProvider())
    result = service.analyze(command_at(79,11))
    assert result["modules"]["water_balance"]["status"] == "completed"
    assert result["irrigation_advisory"]["status"] == "insufficient_data"
    assert result["irrigation_advisory"]["reason_code"] == "HISTORICAL_WEATHER_STALE"


def test_invalid_profile_fails_balance_only_and_skips_advisory():
    repository = InvalidProfileRepository()
    service = AnalysisService(settings(), box(78,10,80,12), repository, PaddyProvider(), PaddyRuntime(), Artifacts(), WeatherProvider())
    result = service.analyze(command_at(79,11))
    assert result["modules"]["weather"]["status"] == "completed"
    assert result["modules"]["water_balance"]["status"] == "failed"
    assert result["modules"]["irrigation_advisory"]["status"] == "skipped"


def test_initial_database_write_failure_is_terminal_and_provider_is_not_called():
    repository, provider = FailingCreateRepository(), Provider()
    service = AnalysisService(settings(), box(78,10,80,12), repository, provider, Runtime(), Artifacts())
    with pytest.raises(DomainError) as error:
        service.analyze(command_at(79,11))
    assert error.value.code == "DATABASE_WRITE_FAILED"
    assert provider.calls == 0
