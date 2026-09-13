from __future__ import annotations

from math import isfinite

IRRIGATION_RULE_VERSION = "paddy-advisory-v1"


def build_irrigation_advisory(
    balance: dict,
    forecast_daily: list[dict],
    *,
    field_area_m2: float,
    irrigation_efficiency: float,
) -> dict:
    if balance.get("status") != "completed":
        return {
            "status": "insufficient_data", "action": "unavailable",
            "reason_code": "WATER_BALANCE_OR_FORECAST_UNAVAILABLE", "provisional": True,
            "evidence_level": "low", "rule_version": IRRIGATION_RULE_VERSION,
            "net_depth_mm": None, "gross_depth_mm": None, "volume_m3": None,
            "warnings": ["A valid water balance is required."],
        }
    area = float(field_area_m2)
    efficiency = float(irrigation_efficiency)
    if not isfinite(area) or area <= 0 or not isfinite(efficiency) or not 0 < efficiency <= 1:
        raise ValueError("field area and irrigation efficiency are invalid")

    current = balance["daily"][-1]
    first_two = forecast_daily[:2]
    credited_rain = sum(
        float(row.get("rainfall_mm", 0)) * (1.0 if row.get("rainfall_is_credited") else 0.8)
        for row in first_two
    )
    current_deficit = float(current["water_deficit_mm"])
    crossing_index = next((index for index, row in enumerate(forecast_daily[:5]) if row.get("trigger_crossed")), None)

    if current.get("trigger_crossed"):
        if credited_rain >= current_deficit and current_deficit > 0:
            action, urgency, net, reason = "delay_for_rain", "low", 0.0, "Credited rain within two days covers the current refill requirement."
        else:
            action, urgency, net, reason = "irrigate_now", "high", current_deficit, "The current paddy water state has crossed its stage-specific trigger."
    elif not forecast_daily:
        action, urgency, net = "monitor", "low", 0.0
        reason = "Current state has not crossed its trigger; forecast is unavailable, so monitor the field."
    elif crossing_index is not None and crossing_index < 2:
        action, urgency = "irrigate_soon", "medium"
        net = float(forecast_daily[crossing_index]["water_deficit_mm"])
        reason = "The projected balance crosses its irrigation trigger within two days."
    elif crossing_index is not None:
        action, urgency, net = "monitor", "low", 0.0
        reason = "The projected balance may cross its trigger in three to five days."
    else:
        action, urgency, net = "no_irrigation_required", "none", 0.0
        reason = "No irrigation trigger is crossed in the five-day projection."

    gross = net / efficiency
    volume = gross * area / 1000.0
    warnings = list(balance.get("warnings", []))
    if not forecast_daily:
        warnings.append("Forecast is unavailable; this recommendation uses current deficit only.")
    return {
        "status": "completed", "action": action, "reason_code": None,
        "provisional": True, "evidence_level": balance.get("evidence_level", "low"),
        "rule_version": IRRIGATION_RULE_VERSION, "urgency": urgency, "reason": reason,
        "net_depth_mm": round(net, 3), "gross_depth_mm": round(gross, 3),
        "volume_m3": round(volume, 3), "irrigation_efficiency": efficiency,
        "forecast_rainfall_credited_mm": round(credited_rain, 3),
        "trigger_crossing_date": None if crossing_index is None else forecast_daily[crossing_index]["date"],
        "warnings": warnings,
    }
