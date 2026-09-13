from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, replace
from datetime import date, timedelta
from math import isfinite

from .contracts import DailyWeather, IrrigationDepth, WaterObservation, WaterState
from .profiles import PROFILE_METADATA, PaddyWaterProfile

WATER_BALANCE_RULE_VERSION = "paddy-daily-v2"


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
    water_observations: list[WaterObservation],
    assimilate_observations: bool,
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
    observations_by_date: dict[date, list[WaterObservation]] = defaultdict(list)
    for observation in water_observations:
        observations_by_date[observation.date].append(observation)

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
        adjusted_depletion_fraction = min(
            0.8, max(0.1, profile.depletion_fraction + 0.04 * (5.0 - potential_etc))
        )
        readily_available = adjusted_depletion_fraction * taw
        if ponded > 0 or root_depletion <= readily_available:
            stress_coefficient = 1.0
        else:
            denominator = (1.0 - adjusted_depletion_fraction) * taw
            stress_coefficient = 0.0 if denominator <= 0 else min(
                1.0, max(0.0, (taw - root_depletion) / denominator)
            )
        root_extraction = min(remaining_etc * stress_coefficient, taw - root_depletion)
        root_depletion += root_extraction
        unmet_etc = remaining_etc - root_extraction
        actual_etc = surface_etc + root_extraction

        state_adjustment = 0.0
        assimilated_types: list[str] = []
        if assimilate_observations:
            for observation in observations_by_date[item.date]:
                if observation.reliability == "low":
                    continue
                if observation.observation_type == "ponded_depth":
                    measured_ponding = min(profile.max_ponding_mm, _finite_nonnegative("ponded depth", observation.value))
                    state_adjustment += measured_ponding - ponded
                    ponded = measured_ponding
                    assimilated_types.append(observation.observation_type)
                elif (
                    observation.observation_type == "volumetric_soil_water"
                    and observation.measurement_depth_m is not None
                    and observation.measurement_depth_m >= profile.root_depth_m
                ):
                    theta = float(observation.value)
                    if not 0 <= theta <= 1:
                        raise ValueError("volumetric soil water must be between zero and one")
                    measured_depletion = min(taw, max(0.0, 1000.0 * (profile.field_capacity - theta) * profile.root_depth_m))
                    state_adjustment += root_depletion - measured_depletion
                    root_depletion = measured_depletion
                    assimilated_types.append(observation.observation_type)
        final_storage = taw - root_depletion + ponded
        residual = initial_storage + inflow + state_adjustment - actual_etc - seepage - runoff - final_storage
        deficit = root_depletion + max(0.0, target_ponding - ponded)
        refill_stage = not stage.startswith(("Maturity", "Post-harvest"))
        if not refill_stage:
            trigger_type = "maturity_exclusion"
        elif root_depletion >= readily_available:
            trigger_type = "root_depletion"
        elif target_ponding > 0 and ponded <= 0:
            trigger_type = "ponding_exhausted"
        else:
            trigger_type = None
        trigger_crossed = trigger_type in {"root_depletion", "ponding_exhausted"}
        rows.append({
            "date": item.date.isoformat(), "kind": item.kind, "stage": stage,
            "days_after_cycle_start": days_after_start, "rainfall_mm": round(rainfall, 6),
            "effective_input_mm": round(inflow - runoff, 6),
            "net_irrigation_mm": round(net_irrigation, 6), "et0_mm": round(et0, 6),
            "kc": round(kc, 6), "potential_etc_mm": round(potential_etc, 6),
            "actual_etc_mm": round(actual_etc, 6), "unmet_etc_mm": round(unmet_etc, 6),
            "stress_coefficient": round(stress_coefficient, 6),
            "depletion_fraction": round(adjusted_depletion_fraction, 6),
            "readily_available_water_mm": round(readily_available, 6),
            "seepage_percolation_mm": round(seepage, 6), "runoff_mm": round(runoff, 6),
            "root_depletion_mm": round(root_depletion, 6), "ponded_water_mm": round(ponded, 6),
            "target_ponding_mm": round(target_ponding, 6), "water_deficit_mm": round(deficit, 6),
            "available_root_water_mm": round(taw - root_depletion, 6),
            "trigger_crossed": trigger_crossed, "trigger_type": trigger_type,
            "state_adjustment_mm": round(state_adjustment, 6),
            "assimilated_observation_types": assimilated_types,
            "conservation_residual_mm": round(residual, 12),
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
    water_observations: list[WaterObservation] | None = None,
    assimilate_observations: bool = True,
) -> dict:
    if weather and weather[0].date < cycle_start:
        weather = [item for item in weather if item.date >= cycle_start]
    if not weather:
        raise ValueError("weather does not cover the crop cycle")
    if initial_state is None:
        _, _, target = profile.stage_parameters((weather[0].date - cycle_start).days)
        initial_state = WaterState(0.0, target)

    water_observations = water_observations or []
    rows, final_state = _simulate(weather, irrigation, profile, cycle_start, initial_state, water_observations, assimilate_observations)
    low_rows, _ = _simulate(weather, irrigation, replace(profile, seepage_percolation_mm_day=profile.seepage_low_mm_day), cycle_start, initial_state, water_observations, assimilate_observations)
    high_rows, _ = _simulate(weather, irrigation, replace(profile, seepage_percolation_mm_day=profile.seepage_high_mm_day), cycle_start, initial_state, water_observations, assimilate_observations)
    latest = rows[-1]
    assimilated = any(row["assimilated_observation_types"] for row in rows)
    evidence_level = "high" if (initial_state_source == "measured" or assimilated) and irrigation_history_complete else (
        "medium" if cycle_start_source in {"transplanting_date", "sowing_date"} and irrigation_history_complete else "low"
    )
    warnings = [
        "Water deficit is provisional until validated against field water-depth and irrigation records.",
    ]
    if not irrigation_history_complete:
        warnings.append("Irrigation history is incomplete; no recorded irrigation is not proof of zero irrigation.")
    if initial_state_source != "measured":
        warnings.append("Initial field-water state uses a versioned stage default.")
    if water_observations and not assimilated:
        warnings.append("Available field-water observations were not eligible for operational state assimilation.")
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
        "readily_available_water_mm": latest["readily_available_water_mm"],
        "cumulative_etc_mm": round(sum(row["actual_etc_mm"] for row in rows), 6),
        "cumulative_rainfall_mm": round(sum(row["rainfall_mm"] for row in rows), 6),
        "cumulative_irrigation_mm": round(sum(row["net_irrigation_mm"] for row in rows), 6),
        "final_state": asdict(final_state), "daily": rows, "warnings": warnings,
        "input_sources": sorted({row["source"] for row in rows}),
        "assumptions": {
            "profile": asdict(profile), "irrigation_history_complete": irrigation_history_complete,
            "water_observation_count": len(water_observations),
            "observations_assimilated": assimilated,
            "assimilation_enabled": assimilate_observations,
            "parameter_metadata": PROFILE_METADATA["parameters"],
            "parameter_sources": PROFILE_METADATA["sources"],
        },
    }
