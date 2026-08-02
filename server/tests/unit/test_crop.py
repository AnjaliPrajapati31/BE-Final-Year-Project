import numpy as np
import pytest

from app.services.sickle.contracts import CropInputs, Grid
from app.services.sickle.crop import DAY_POSITIONS, S2_BANDS, summarize_crop, validate_crop_inputs

pytestmark = pytest.mark.unit


def inputs():
    mask = np.zeros((32, 32), dtype=bool); mask[12:20, 12:20] = True
    return CropInputs(np.ones((1, 2, 32, 32), np.float32), np.array([DAY_POSITIONS["June"]]), ["June"], np.ones((1, 12, 32, 32), np.float32) * 1000, np.array([DAY_POSITIONS["June"]]), ["June"], mask, Grid("EPSG:32644", (10, 0, 0, 0, -10, 320)), [], "test", False)


def test_exact_band_and_day_contract():
    assert len(S2_BANDS) == 12
    assert DAY_POSITIONS == {"June": 15, "July": 45, "August": 76, "September": 107, "October": 137}


def test_crop_summary_uses_only_field_pixels():
    item = inputs(); validate_crop_inputs(item)
    probabilities = np.zeros((2, 32, 32), np.float32); probabilities[0] = 0.2; probabilities[1] = 0.8
    probabilities[0, item.field_mask] = 0.7; probabilities[1, item.field_mask] = 0.3
    result = summarize_crop(probabilities, item.field_mask, item)
    assert result["class_label"] == "Paddy"
    assert result["paddy_probability"] == pytest.approx(0.7)
