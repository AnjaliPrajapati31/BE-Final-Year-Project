from __future__ import annotations

from collections.abc import Iterable
from math import isfinite, sqrt


def _finite_number(value, label: str) -> float:
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def paired_error_metrics(rows: Iterable[dict], estimated_key: str, observed_key: str) -> dict:
    pairs: list[tuple[float, float]] = []
    for row in rows:
        estimated = row.get(estimated_key)
        observed = row.get(observed_key)
        if estimated in (None, "") or observed in (None, ""):
            continue
        pairs.append((_finite_number(estimated, estimated_key), _finite_number(observed, observed_key)))
    if not pairs:
        return {"sample_count": 0, "bias": None, "mae": None, "rmse": None}
    errors = [estimated - observed for estimated, observed in pairs]
    count = len(errors)
    return {
        "sample_count": count,
        "bias": sum(errors) / count,
        "mae": sum(abs(error) for error in errors) / count,
        "rmse": sqrt(sum(error * error for error in errors) / count),
    }


def build_validation_report(fields: list[dict]) -> dict:
    all_rows = [row for field in fields for row in field.get("observations", [])]
    field_count = len({field.get("field_id") for field in fields if field.get("field_id")})
    dry_down_count = sum(bool(field.get("has_dry_down_event")) for field in fields)
    refill_count = sum(bool(field.get("has_rainfall_or_irrigation_refill_event")) for field in fields)
    residuals = [
        abs(_finite_number(row["conservation_residual_mm"], "conservation_residual_mm"))
        for row in all_rows if row.get("conservation_residual_mm") not in (None, "")
    ]
    metrics = {
        "rainfall_mm": paired_error_metrics(all_rows, "estimated_rainfall_mm", "observed_rainfall_mm"),
        "et0_mm": paired_error_metrics(all_rows, "calculated_et0_mm", "reference_et0_mm"),
        "ponded_water_mm": paired_error_metrics(all_rows, "estimated_ponded_water_mm", "observed_ponded_water_mm"),
        "root_depletion_mm": paired_error_metrics(all_rows, "estimated_root_depletion_mm", "observed_root_depletion_mm"),
        "maximum_conservation_residual_mm": max(residuals, default=None),
    }
    water_pair_counts = []
    weather_pair_counts = []
    for field in fields:
        observations = field.get("observations", [])
        water_pair_counts.append(sum(
            (row.get("estimated_ponded_water_mm") not in (None, "") and row.get("observed_ponded_water_mm") not in (None, ""))
            or (row.get("estimated_root_depletion_mm") not in (None, "") and row.get("observed_root_depletion_mm") not in (None, ""))
            for row in observations
        ))
        weather_pair_counts.append(sum(
            row.get("estimated_rainfall_mm") not in (None, "")
            and row.get("observed_rainfall_mm") not in (None, "")
            and row.get("calculated_et0_mm") not in (None, "")
            and row.get("reference_et0_mm") not in (None, "")
            for row in observations
        ))
    requirements = {
        "at_least_five_fields": field_count >= 5,
        "unique_nonempty_field_ids": field_count == len(fields) and field_count > 0,
        "known_paddy_labels": bool(fields) and all(field.get("known_crop_label") == "Paddy" for field in fields),
        "cycle_dates_present": bool(fields) and all(
            field.get("sowing_date") or field.get("transplanting_date") for field in fields
        ),
        "soil_descriptions_present": bool(fields) and all(field.get("soil_description") for field in fields),
        "irrigation_history_complete": bool(fields) and all(
            field.get("irrigation_history_coverage") == "complete" for field in fields
        ),
        "validation_assimilation_disabled": bool(fields) and all(
            field.get("assimilation_enabled") is False for field in fields
        ),
        "dry_down_event_present": dry_down_count >= 1,
        "refill_event_present": refill_count >= 1,
        "rainfall_pairs_present": metrics["rainfall_mm"]["sample_count"] > 0,
        "et0_pairs_present": metrics["et0_mm"]["sample_count"] > 0,
        "field_water_pairs_present": (
            metrics["ponded_water_mm"]["sample_count"] > 0
            or metrics["root_depletion_mm"]["sample_count"] > 0
        ),
        "at_least_ten_water_pairs_per_field": bool(fields) and all(count >= 10 for count in water_pair_counts),
        "at_least_ten_weather_pairs_per_field": bool(fields) and all(count >= 10 for count in weather_pair_counts),
        "mass_conservation_verified": bool(residuals) and max(residuals) < 1e-6,
    }
    ready = all(requirements.values())
    return {
        "status": "validation_complete" if ready else "insufficient_validation_data",
        "water_deficit_accuracy_publishable": ready,
        "field_count": field_count,
        "observation_count": len(all_rows),
        "water_pair_counts_by_field": {
            str(field.get("field_id")): count for field, count in zip(fields, water_pair_counts)
        },
        "weather_pair_counts_by_field": {
            str(field.get("field_id")): count for field, count in zip(fields, weather_pair_counts)
        },
        "dry_down_field_count": dry_down_count,
        "refill_field_count": refill_count,
        "requirements": requirements,
        "metrics": metrics,
        "warning": None if ready else (
            "Water-balance and advisory outputs must remain provisional until every validation requirement passes."
        ),
    }
