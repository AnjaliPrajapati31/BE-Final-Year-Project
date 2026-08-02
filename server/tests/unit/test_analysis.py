from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
from shapely.geometry import box

from app.core.exceptions import DomainError
from app.schemas.field_analysis import FieldAnalysisRequest
from app.services.sickle.analysis import AnalysisService
from app.services.sickle.contracts import CropInputs, Grid

pytestmark = pytest.mark.unit


class Repository:
    def __init__(self):
        self.created = 0
        self.statuses = []

    def verify_roi(self, field, patch): return uuid4()
    def create_revision_and_run(self, *args): self.created += 1
    def set_status(self, request_id, status, **kwargs): self.statuses.append(status)
    def save_crop(self, *args): pass
    def save_stage(self, *args): pass
    def save_crop_quality(self, *args): pass
    def set_provider_cached(self, *args): pass


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


class Artifacts: pass


def settings():
    return SimpleNamespace(FIELD_MAX_VERTICES=10000,FIELD_MIN_AREA_M2=100,FIELD_MAX_AREA_M2=78400,FIELD_MAX_WIDTH_M=280,FIELD_MAX_HEIGHT_M=280,CAUVERY_ROI_VERSION=1)


def command_at(lon, lat):
    return FieldAnalysisRequest.model_validate({"field_id":"FIELD_001","geometry":{"type":"Polygon","coordinates":[[[lon,lat],[lon+0.001,lat],[lon+0.001,lat+0.001],[lon,lat+0.001],[lon,lat]]]},"year":2025})


def test_non_paddy_completes_without_stage_provider_call():
    repository, provider = Repository(), Provider()
    service = AnalysisService(settings(), box(78,10,80,12), repository, provider, Runtime(), Artifacts())
    result = service.analyze(command_at(79,11))
    assert result["crop"]["class_label"] == "Non-Paddy"
    assert result["growth_stage"]["reason_code"] == "NON_PADDY_STAGE_SKIPPED"
    assert repository.created == 1 and provider.calls == 1


def test_outside_roi_never_creates_or_calls_provider():
    repository, provider = Repository(), Provider()
    service = AnalysisService(settings(), box(78,10,80,12), repository, provider, Runtime(), Artifacts())
    with pytest.raises(DomainError) as error:
        service.analyze(command_at(82,15))
    assert error.value.code == "OUTSIDE_SUPPORTED_ROI"
    assert repository.created == 0 and provider.calls == 0
