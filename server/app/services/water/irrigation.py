from __future__ import annotations

from math import isfinite


def normalize_irrigation(amount: float, unit: str, field_area_m2: float, efficiency: float) -> tuple[float, float]:
    amount = float(amount)
    area = float(field_area_m2)
    efficiency = float(efficiency)
    if not isfinite(amount) or amount <= 0 or not isfinite(area) or area <= 0:
        raise ValueError("irrigation amount and field area must be positive finite values")
    if unit not in {"mm", "m3"}:
        raise ValueError("irrigation unit must be mm or m3")
    if not isfinite(efficiency) or not 0 < efficiency <= 1:
        raise ValueError("application efficiency must be greater than zero and at most one")
    gross_depth = amount if unit == "mm" else amount * 1000.0 / area
    return gross_depth, gross_depth * efficiency
