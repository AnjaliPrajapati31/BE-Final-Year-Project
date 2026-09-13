from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal


@dataclass(frozen=True)
class DailyWeather:
    date: date
    rainfall_mm: float
    et0_mm: float
    kind: Literal["historical", "forecast"] = "historical"
    source: str = "fixture"
    quality: Any = field(default_factory=dict)


@dataclass(frozen=True)
class IrrigationDepth:
    date: date
    net_depth_mm: float


@dataclass(frozen=True)
class WaterState:
    root_depletion_mm: float
    ponded_water_mm: float
