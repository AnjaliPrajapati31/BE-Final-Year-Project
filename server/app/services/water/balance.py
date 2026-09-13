from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, replace
from datetime import date, timedelta
from math import isfinite

from .contracts import DailyWeather, IrrigationDepth, WaterState
from .profiles import PROFILE_METADATA, PaddyWaterProfile

WATER_BALANCE_RULE_VERSION = "paddy-daily-v1"


def _finite_nonnegative(name: str, value: float) -> float:
    number = float(value)
    if not isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return number


def validate_profile(profile: PaddyWaterProfile) -> None:
    if not 0 < profile.field_capacity <= 1 or not 0 <= profile.wilting_point < profile.field_capacity:
        raise ValueError("field capacity and wilting point are invalid")
    if not 0 < profile.root_depth_m <= 3:
        raise ValueError("root depth is invalid")
    if not 0 < profile.depletion_fraction <= 1:
        raise ValueError("depletion fraction is invalid")
    if not 0 < profile.irrigation_efficiency <= 1:
        raise ValueError("irrigation efficiency is invalid")
    for name in ("seepage_percolation_mm_day", "seepage_low_mm_day", "seepage_high_mm_day", "max_ponding_mm"):
        _finite_nonnegative(name, getattr(profile, name))
    for name, details in PROFILE_METADATA["parameters"].items():
        lower, upper = details["valid_range"]
        value = float(getattr(profile, name))
        if not lower <= value <= upper:
            raise ValueError(f"{name} must be within {lower:g}–{upper:g} {details['unit']}")


def _simulate(
    weather: list[DailyWeather],
    irrigation: list[IrrigationDepth],
    profile: PaddyWaterProfile,
    cycle_start: date,
    initial_state: WaterState,
) -> tuple[list[dict], WaterState]:
    validate_profile(profile)
    ordered = sorted(weather, key=lambda item: item.date)
    if not ordered:
        raise ValueError("at least one daily weather row is required")
    if len({item.date for item in ordered}) != len(ordered):
        raise ValueError("daily weather dates must be unique")
    for previous, current in zip(ordered, ordered[1:]):
        if current.date != previous.date + timedelta(days=1):
            raise ValueError("daily weather must be consecutive")
    irrigation_by_date: dict[date, float] = defaultdict(float)
    for event in irrigation:
        irrigation_by_date[event.date] += _finite_nonnegative("irrigation depth", event.net_depth_mm)

    taw = profile.total_available_water_mm
    root_depletion = min(taw, _finite_nonnegative("initial root depletion", initial_state.root_depletion_mm))
    ponded = min(profile.max_ponding_mm, _finite_nonnegative("initial ponded water", initial_state.ponded_water_mm))
    rows: list[dict] = []

    for item in ordered:
        rainfall = _finite_nonnegative("rainfall", item.rainfall_mm)
        et0 = _finite_nonnegative("ET0", item.et0_mm)
        net_irrigation = irrigation_by_date[item.date]
        days_after_start = (item.date - cycle_start).days
        stage, kc, target_ponding = profile.stage_parameters(days_after_start)
        potential_etc = et0 * kc

        initial_storage = taw - root_depletion + ponded
        inflow = rainfall + net_irrigation
        recharge = min(root_depletion, inflow)
        root_depletion -= recharge
        surface_inflow = inflow - recharge
        ponded += surface_inflow
        runoff = max(0.0, ponded - profile.max_ponding_mm)
        ponded -= runoff

        seepage = min(profile.seepage_percolation_mm_day, ponded)
        ponded -= seepage
        surface_etc = min(potential_etc, ponded)
        ponded -= surface_etc
        remaining_etc = potential_etc - surface_etc
        depletion_before_limit = root_depletion + remaining_etc
        root_depletion = min(taw, depletion_before_limit)
        unmet_etc = max(0.0, depletion_before_limit - taw)
        actual_etc = potential_etc - unmet_etc

        final_storage = taw - root_depletion + ponded
        residual = initial_storage + inflow - actual_etc - seepage - runoff - final_storage
        deficit = root_depletion + max(0.0, target_ponding - ponded)
        refill_stage = not stage.startswith(("Maturity", "Post-harvest"))
        trigger_crossed = refill_stage and (root_depletion >= profile.readily_available_water_mm or (
            target_ponding > 0 and ponded <= 0
        ))
        rows.append({
            "date": item.date.isoformat(), "kind": item.kind, "stage": stage,
            "days_after_cycle_start": days_after_start, "rainfall_mm": round(rainfall, 6),
            "effective_input_mm": round(inflow - runoff, 6),
            "net_irrigation_mm": round(net_irrigation, 6), "et0_mm": round(et0, 6),
            "kc": round(kc, 6), "potential_etc_mm": round(potential_etc, 6),
            "actual_etc_mm": round(actual_etc, 6), "unmet_etc_mm": round(unmet_etc, 6),
            "seepage_percolation_mm": round(seepage, 6), "runoff_mm": round(runoff, 6),
            "root_depletion_mm": round(root_depletion, 6), "ponded_water_mm": round(ponded, 6),
            "target_ponding_mm": round(target_ponding, 6), "water_deficit_mm": round(deficit, 6),
            "available_root_water_mm": round(taw - root_depletion, 6),
            "trigger_crossed": trigger_crossed, "conservation_residual_mm": round(residual, 12),
            "source": item.source, "quality": item.quality,
        })
    return rows, WaterState(root_depletion, ponded)


def calculate_paddy_balance(
    weather: list[DailyWeather],
    irrigation: list[IrrigationDepth],
    profile: PaddyWaterProfile,
    cycle_start: date,
    *,
    initial_state: WaterState | None = None,
    initial_state_source: str = "stage_default",
    cycle_start_source: str = "satellite_stage",
    irrigation_history_complete: bool = False,
) -> dict:
    if weather and weather[0].date < cycle_start:
        weather = [item for item in weather if item.date >= cycle_start]
    if not weather:
        raise ValueError("weather does not cover the crop cycle")
    if initial_state is None:
        _, _, target = profile.stage_parameters((weather[0].date - cycle_start).days)
        initial_state = WaterState(0.0, target)

    rows, final_state = _simulate(weather, irrigation, profile, cycle_start, initial_state)
    low_rows, _ = _simulate(weather, irrigation, replace(profile, seepage_percolation_mm_day=profile.seepage_low_mm_day), cycle_start, initial_state)
    high_rows, _ = _simulate(weather, irrigation, replace(profile, seepage_percolation_mm_day=profile.seepage_high_mm_day), cycle_start, initial_state)
    latest = rows[-1]
    evidence_level = "high" if initial_state_source == "measured" and irrigation_history_complete else (
        "medium" if cycle_start_source in {"transplanting_date", "sowing_date"} and irrigation_history_complete else "low"
    )
    warnings = [
        "Water deficit is provisional until validated against field water-depth and irrigation records.",
    ]
    if not irrigation_history_complete:
        warnings.append("Irrigation history is incomplete; no recorded irrigation is not proof of zero irrigation.")
    if initial_state_source != "measured":
        warnings.append("Initial field-water state uses a versioned stage default.")
    return {
        "status": "completed", "reason_code": None, "provisional": True,
        "evidence_level": evidence_level, "rule_version": WATER_BALANCE_RULE_VERSION,
        "profile_version": profile.version, "cycle_start": cycle_start.isoformat(),
        "cycle_start_source": cycle_start_source, "initial_state_source": initial_state_source,
        "as_of_date": latest["date"], "water_deficit_mm": latest["water_deficit_mm"],
        "water_deficit_low_mm": low_rows[-1]["water_deficit_mm"],
        "water_deficit_high_mm": high_rows[-1]["water_deficit_mm"],
        "root_depletion_mm": latest["root_depletion_mm"], "ponded_water_mm": latest["ponded_water_mm"],
        "total_available_water_mm": round(profile.total_available_water_mm, 6),
        "readily_available_water_mm": round(profile.readily_available_water_mm, 6),
        "cumulative_etc_mm": round(sum(row["actual_etc_mm"] for row in rows), 6),
        "cumulative_rainfall_mm": round(sum(row["rainfall_mm"] for row in rows), 6),
        "cumulative_irrigation_mm": round(sum(row["net_irrigation_mm"] for row in rows), 6),
        "final_state": asdict(final_state), "daily": rows, "warnings": warnings,
        "input_sources": sorted({row["source"] for row in rows}),
        "assumptions": {
            "profile": asdict(profile), "irrigation_history_complete": irrigation_history_complete,
            "parameter_metadata": PROFILE_METADATA["parameters"],
            "parameter_sources": PROFILE_METADATA["sources"],
        },
    }
