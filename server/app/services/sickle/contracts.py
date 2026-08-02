from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Grid:
    crs: str
    transform: tuple[float, float, float, float, float, float]
    width: int = 32
    height: int = 32


@dataclass
class ObservationQuality:
    sensor: str
    month: str
    day_position: int
    accepted: bool
    zero_fraction: float
    source_ids: list[str] = field(default_factory=list)
    valid_pixel_count: int | None = None
    valid_pixel_fraction: float | None = None
    rejection_reason: str | None = None


@dataclass
class CropInputs:
    s1: np.ndarray
    s1_dates: np.ndarray
    s1_months: list[str]
    s2: np.ndarray
    s2_dates: np.ndarray
    s2_months: list[str]
    field_mask: np.ndarray
    grid: Grid
    quality: list[ObservationQuality]
    provider: str
    live_data: bool
    cached: bool = False


@dataclass(frozen=True)
class DetailedObservation:
    sensor: str
    date: str
    values: dict[str, Any]
    source_image_id: str | None = None
