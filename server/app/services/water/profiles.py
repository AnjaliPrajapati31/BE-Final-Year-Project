from __future__ import annotations

from dataclasses import dataclass
import json

from app.config import BASE_DIR


@dataclass(frozen=True)
class PaddyWaterProfile:
    version: str
    field_capacity: float
    wilting_point: float
    root_depth_m: float
    depletion_fraction: float
    seepage_percolation_mm_day: float
    seepage_low_mm_day: float
    seepage_high_mm_day: float
    irrigation_efficiency: float
    max_ponding_mm: float

    @property
    def total_available_water_mm(self) -> float:
        return 1000.0 * (self.field_capacity - self.wilting_point) * self.root_depth_m

    @property
    def readily_available_water_mm(self) -> float:
        return self.depletion_fraction * self.total_available_water_mm

    def stage_parameters(self, days_after_start: int) -> tuple[str, float, float]:
        """Return stage, single Kc and target ponding depth for a crop-cycle day."""
        if days_after_start <= 20:
            return "Establishment / Transplanting", 1.05, 25.0
        if days_after_start <= 55:
            fraction = (days_after_start - 20) / 35.0
            return "Vegetative / Tillering", 1.05 + 0.15 * fraction, 30.0
        if days_after_start <= 90:
            return "Reproductive / Grain formation", 1.20, 50.0
        if days_after_start <= 120:
            fraction = (days_after_start - 90) / 30.0
            return "Maturity / Harvest", 0.90 - 0.30 * fraction, 0.0
        return "Post-harvest", 0.0, 0.0


PROFILE_METADATA = json.loads((BASE_DIR / "resources/water/cauvery-paddy-v1.json").read_text(encoding="utf-8"))
_VALUES = {name: details["value"] for name, details in PROFILE_METADATA["parameters"].items()}

# Provisional defaults are loaded from the versioned resource above.
CAUVERY_PADDY_V1 = PaddyWaterProfile(
    version=PROFILE_METADATA["version"],
    **_VALUES,
)
