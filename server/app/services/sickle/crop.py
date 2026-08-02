from __future__ import annotations

import numpy as np

from app.core.exceptions import DomainError

from .contracts import CropInputs

PREPROCESSING_VERSION = "sickle-cauvery-v2-s2-cloud15"
MONTHS = ["June", "July", "August", "September", "October"]
DAY_POSITIONS = {"June": 15, "July": 45, "August": 76, "September": 107, "October": 137}
S1_BANDS = ["VV", "VH"]
S2_BANDS = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B9", "B11", "B12"]


def validate_crop_inputs(inputs: CropInputs) -> None:
    expected = ((2, 32, 32), (12, 32, 32))
    if inputs.s1.ndim != 4 or tuple(inputs.s1.shape[1:]) != expected[0]:
        raise DomainError("INSUFFICIENT_SENTINEL1", "Sentinel-1 input has an invalid shape.")
    if inputs.s2.ndim != 4 or tuple(inputs.s2.shape[1:]) != expected[1]:
        raise DomainError("INSUFFICIENT_SENTINEL2", "Sentinel-2 input has an invalid shape.")
    if inputs.s1.shape[0] < 1 or len(inputs.s1_dates) != inputs.s1.shape[0]:
        raise DomainError("INSUFFICIENT_SENTINEL1", "No usable Sentinel-1 observation is available.")
    if inputs.s2.shape[0] < 1 or len(inputs.s2_dates) != inputs.s2.shape[0]:
        raise DomainError("INSUFFICIENT_SENTINEL2", "No usable Sentinel-2 observation is available.")
    if inputs.field_mask.shape != (32, 32) or not np.any(inputs.field_mask):
        raise DomainError("NO_OVERLAPPING_RASTER", "The field mask contains no pixels.")
    mask = inputs.field_mask.astype(bool)
    if mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any():
        raise DomainError("FIELD_DOES_NOT_FIT_PATCH", "The field reaches the 32×32 patch edge.")
    if not np.isfinite(inputs.s1).all() or not np.isfinite(inputs.s2).all():
        raise DomainError("CROP_INFERENCE_FAILED", "Crop inputs contain non-finite values.")


def summarize_crop(probabilities: np.ndarray, field_mask: np.ndarray, inputs: CropInputs) -> dict:
    if probabilities.shape != (2, 32, 32):
        raise DomainError("CROP_INFERENCE_FAILED", "Unexpected crop probability shape.", 500)
    mask = field_mask.astype(bool)
    means = probabilities[:, mask].mean(axis=1)
    pixel_classes = probabilities.argmax(axis=0)[mask]
    predicted = int(means.argmax())
    labels = {0: "Paddy", 1: "Non-Paddy"}
    return {
        "class_code": predicted,
        "class_label": labels[predicted],
        "confidence": float(means[predicted]),
        "paddy_probability": float(means[0]),
        "non_paddy_probability": float(means[1]),
        "paddy_pixel_fraction": float(np.mean(pixel_classes == 0)),
        "non_paddy_pixel_fraction": float(np.mean(pixel_classes == 1)),
        "field_pixel_count": int(mask.sum()),
        "s1_observation_count": int(inputs.s1.shape[0]),
        "s2_observation_count": int(inputs.s2.shape[0]),
        "s1_months_used": inputs.s1_months,
        "s2_months_used": inputs.s2_months,
        "experimental": True,
    }
