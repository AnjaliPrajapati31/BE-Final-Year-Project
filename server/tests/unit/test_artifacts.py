from uuid import uuid4

import numpy as np
import pytest
import rasterio

from app.core.exceptions import DomainError
from app.services.sickle.artifacts import ArtifactWriter
from app.services.sickle.contracts import CropInputs, Grid

pytestmark = pytest.mark.unit


def test_artifacts_are_managed_and_geotiff_masks_outside_field(tmp_path):
    mask = np.zeros((32, 32), bool); mask[12:20, 12:20] = True
    inputs = CropInputs(np.ones((1,2,32,32),np.float32),np.array([15]),["June"],np.ones((1,12,32,32),np.float32),np.array([15]),["June"],mask,Grid("EPSG:32644",(10,0,500000,0,-10,1200000)),[],"test",False)
    probabilities = np.empty((2,32,32),np.float32); probabilities[0]=0.7; probabilities[1]=0.3
    crop = {"class_label":"Paddy","paddy_probability":0.7,"months":["June"]}
    stage = {"status":"completed","stage":"Vegetative / Tillering","timeline":[{"date":"2025-10-11","ndvi":0.26},{"date":"2025-10-31","ndvi":0.79}]}
    request_id = uuid4(); writer = ArtifactWriter(tmp_path, True)
    records, warnings = writer.write_analysis(request_id, crop, stage, probabilities, inputs)
    assert warnings == []
    assert len(records) == 7
    assert all((tmp_path / record["relative_path"]).is_file() for record in records)
    geotiff = next(record for record in records if record["type"] == "crop_probability")
    with rasterio.open(tmp_path / geotiff["relative_path"]) as dataset:
        array = dataset.read()[0]
        assert dataset.nodata == -9999.0
        assert array[0, 0] == -9999.0
        assert array[15, 15] == pytest.approx(0.7)


def test_artifact_generation_continues_when_one_artifact_fails(tmp_path, monkeypatch):
    mask = np.zeros((32, 32), bool); mask[12:20, 12:20] = True
    inputs = CropInputs(np.ones((1,2,32,32),np.float32),np.array([15]),["June"],np.ones((1,12,32,32),np.float32),np.array([15]),["June"],mask,Grid("EPSG:32644",(10,0,500000,0,-10,1200000)),[],"test",False)
    probabilities = np.empty((2,32,32),np.float32); probabilities[0]=0.7; probabilities[1]=0.3
    crop = {"class_label":"Paddy","paddy_probability":0.7,"months":["June"]}
    stage = {"status":"completed","stage":"Vegetative / Tillering","timeline":[{"date":"2025-10-11","ndvi":0.26},{"date":"2025-10-31","ndvi":0.79}]}
    writer = ArtifactWriter(tmp_path, True)

    def fail_geotiff(*args, **kwargs):
        raise DomainError("ARTIFACT_WRITE_FAILED", "Could not create the crop GeoTIFF artifact.", 500)

    monkeypatch.setattr(writer, "write_crop_geotiff", fail_geotiff)
    records, warnings = writer.write_analysis(uuid4(), crop, stage, probabilities, inputs)
    assert warnings == ["Could not create the crop GeoTIFF artifact."]
    assert any(record["type"] == "crop_summary_json" for record in records)
    assert all(record["type"] != "crop_probability" for record in records)


def test_water_balance_and_advisory_artifacts_are_emitted(tmp_path):
    mask = np.zeros((32, 32), bool); mask[12:20, 12:20] = True
    inputs = CropInputs(np.ones((1,2,32,32),np.float32),np.array([15]),["June"],np.ones((1,12,32,32),np.float32),np.array([15]),["June"],mask,Grid("EPSG:32644",(10,0,500000,0,-10,1200000)),[],"test",False)
    probabilities = np.empty((2,32,32),np.float32); probabilities[0]=0.7; probabilities[1]=0.3
    water_balance = {
        "status": "completed", "water_deficit_mm": 12.5,
        "daily": [{"date": "2025-07-01", "rainfall_mm": 2, "et0_mm": 4, "water_deficit_mm": 12.5}],
    }
    advisory = {"status": "completed", "action": "irrigate_now", "gross_depth_mm": 20, "volume_m3": 200}
    records, warnings = ArtifactWriter(tmp_path, True).write_analysis(
        uuid4(), {"class_label": "Paddy"}, {"status": "completed", "timeline": []},
        probabilities, inputs, water_balance=water_balance, irrigation_advisory=advisory,
    )
    assert warnings == []
    types = {record["type"] for record in records}
    water_types = {"water_balance_summary_json", "water_balance_daily_csv", "irrigation_advisory_json"}
    assert water_types <= types
    assert all(
        (tmp_path / record["relative_path"]).stat().st_size > 0
        for record in records if record["type"] in water_types
    )
