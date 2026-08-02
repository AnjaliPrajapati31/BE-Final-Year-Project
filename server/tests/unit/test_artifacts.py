from uuid import uuid4

import numpy as np
import pytest
import rasterio

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
    records = writer.write_analysis(request_id, crop, stage, probabilities, inputs)
    assert len(records) == 7
    assert all((tmp_path / record["relative_path"]).is_file() for record in records)
    geotiff = next(record for record in records if record["type"] == "crop_probability")
    with rasterio.open(tmp_path / geotiff["relative_path"]) as dataset:
        array = dataset.read(1)
        assert dataset.nodata == -9999.0
        assert array[0, 0] == -9999.0
        assert array[15, 15] == pytest.approx(0.7)
