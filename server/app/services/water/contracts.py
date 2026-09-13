from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal


@dataclass(frozen=True)
class DailyWeather:
    date: date
    rainfall_mm: float
    et0_mm: float
    kind: Literal["historical", "forecast"] = "historical"
    source: str = "fixture"
    quality: Any = field(default_factory=dict)
    raw_variables: dict[str, Any] = field(default_factory=dict)
    model_creation_time: datetime | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    spatial_resolution_m: float | None = None


@dataclass(frozen=True)
class IrrigationDepth:
    date: date
    net_depth_mm: float


@dataclass(frozen=True)
class WaterState:
    root_depletion_mm: float
    ponded_water_mm: float


@dataclass(frozen=True)
class WaterObservation:
    date: date
    observation_type: Literal["ponded_depth", "water_table_depth", "volumetric_soil_water"]
    value: float
    source: str = "measured"
    reliability: Literal["high", "medium", "low"] = "medium"
    measurement_depth_m: float | None = None
