"""Deterministic paddy water-balance and irrigation-advisory domain services."""

from .advisory import build_irrigation_advisory
from .balance import calculate_paddy_balance
from .profiles import CAUVERY_PADDY_V1, PaddyWaterProfile

__all__ = ["CAUVERY_PADDY_V1", "PaddyWaterProfile", "calculate_paddy_balance", "build_irrigation_advisory"]
