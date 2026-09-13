"""
Moisture-stress risk estimation — Phase 1 (satellite-only, provisional).

This module uses the same Sentinel-1 / Sentinel-2 detailed time-series
already fetched by EarthEngineProvider.detailed_series() during growth-stage
estimation.  No additional Earth Engine calls are made.

Scientific approach
-------------------
Rather than fixed thresholds (e.g. "NDMI < 0.2 = stressed"), this module
compares every field against its own recent-cycle baseline using the median
and median absolute deviation (MAD) — robust statistics that are not
distorted by a single outlier observation.

Output categories
-----------------
  "No stress evidence"   — score < 0.20
  "Possible stress"      — score 0.20–0.39
  "Moderate stress risk" — score 0.40–0.59
  "High stress risk"     — score >= 0.60
  status="insufficient_data" — when the data-quality gate fails
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .contracts import DetailedObservation

STRESS_RULE_VERSION = "provisional-cauvery-v1"

WARNING = (
    "This is a provisional satellite-based moisture-stress risk estimate. "
    "Satellite signals can be affected by cloud cover, crop senescence, "
    "harvest, transplanting, flooded conditions, disease, or sensor artefacts. "
    "Satellite evidence does not confirm that water shortage is the cause."
)

_RISK_LABELS = [
    (0.60, "High stress risk"),
    (0.40, "Moderate stress risk"),
    (0.20, "Possible stress"),
    (0.00, "No stress evidence"),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_frame(observations: list[DetailedObservation], sensor: str) -> pd.DataFrame:
    rows = [
        {"date": item.date, **item.values, "source_image_id": item.source_image_id}
        for item in observations
        if item.sensor == sensor
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def _coerce(frame: pd.DataFrame, names: list[str]) -> None:
    for name in names:
        if name not in frame.columns:
            frame[name] = np.nan
        frame[name] = pd.to_numeric(frame[name], errors="coerce")


def _mad(series: pd.Series) -> float:
    """Median absolute deviation — robust spread estimator."""
    median = series.median()
    return float((series - median).abs().median())


def _clean_s2(frame: pd.DataFrame, cycle_start: pd.Timestamp | None) -> pd.DataFrame | None:
    """Return cleaned S2 observations within the active crop cycle."""
    if frame.empty:
        return None
    _coerce(frame, ["NDVI_median", "NDMI_median", "NDWI_median",
                    "valid_pixel_count", "NDVI_count", "scene_cloud_percentage"])
    if frame["valid_pixel_count"].isna().all():
        frame["valid_pixel_count"] = frame["NDVI_count"]
    frame = frame.dropna(subset=["NDVI_median", "NDMI_median", "valid_pixel_count"])
    frame = frame[
        (frame["valid_pixel_count"] > 0)
        & frame["NDVI_median"].between(-1, 1)
        & frame["NDMI_median"].between(-1, 1)
    ]
    if frame.empty:
        return None
    # Cloud filter: drop severely contaminated scenes
    if "scene_cloud_percentage" in frame.columns:
        frame = frame[
            frame["scene_cloud_percentage"].isna()
            | (frame["scene_cloud_percentage"] < 80)
        ]
    if frame.empty:
        return None
    # Restrict to current cycle if cycle_start is known
    if cycle_start is not None:
        frame = frame[frame["date"] >= cycle_start]
    return frame if not frame.empty else None


def _clean_s1(frame: pd.DataFrame, preferred_pass: str | None, preferred_orbit: int | None, cycle_start: pd.Timestamp | None) -> pd.DataFrame | None:
    """Return cleaned S1 observations on the dominant orbit within the active cycle."""
    if frame.empty:
        return None
    rename = {
        "orbitProperties_pass": "orbit_pass",
        "relativeOrbitNumber_start": "orbit_number",
        "relative_orbit_number": "orbit_number",
    }
    frame = frame.rename(columns=rename)
    _coerce(frame, ["VV_median", "VH_median", "VV_minus_VH_median",
                    "valid_pixel_count", "VV_count", "orbit_number"])
    if frame["valid_pixel_count"].isna().all():
        frame["valid_pixel_count"] = frame["VV_count"]
    frame = frame.dropna(subset=["VV_median", "VH_median", "valid_pixel_count"])
    frame = frame[frame["valid_pixel_count"] > 0]
    if frame.empty:
        return None
    # Filter to the orbit already selected by the stage module
    if preferred_pass is not None and "orbit_pass" in frame.columns:
        frame = frame[frame["orbit_pass"].astype(str) == preferred_pass]
    if preferred_orbit is not None:
        frame = frame[
            pd.to_numeric(frame["orbit_number"], errors="coerce") == preferred_orbit
        ]
    if frame.empty:
        return None
    # Restrict to current cycle
    if cycle_start is not None:
        frame = frame[frame["date"] >= cycle_start]
    return frame if not frame.empty else None


def _risk_label(score: float) -> str:
    for threshold, label in _RISK_LABELS:
        if score >= threshold:
            return label
    return "No stress evidence"


# ---------------------------------------------------------------------------
# Data-quality gate
# ---------------------------------------------------------------------------

def _gate_failure(reason_code: str, message: str, status: str = "insufficient_data") -> dict[str, Any]:
    return {
        "status": status,
        "reason_code": reason_code,
        "provisional": True,
        "stress_risk": None,
        "stress_score": None,
        "latest_observation_date": None,
        "persistence_observations": None,
        "stage_context": None,
        "stage_evidence": None,
        "evidence": [],
        "counter_evidence": [],
        "warning": message,
        "chart_data": {"optical": [], "radar": []},
        "stress_rule_version": STRESS_RULE_VERSION,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def estimate_stress(
    observations: list[DetailedObservation],
    stage: dict[str, Any],
    crop: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute provisional moisture-stress risk from existing S1/S2 time-series.

    Parameters
    ----------
    observations : list[DetailedObservation]
        The same detailed observation list returned by EarthEngineProvider.detailed_series().
    stage : dict
        Output from estimate_stage(). Provides cycle_start, stage label, evidence,
        and selected S1 orbit information.
    crop : dict
        Output from summarize_crop(). Used only to embed crop label in output.

    Returns
    -------
    dict with fields matching the stress_results DB table schema plus chart_data.
    """
    # --- Gate 0: Only run for Paddy -----------------------------------------
    if crop.get("class_label") != "Paddy":
        return _gate_failure(
            "NON_PADDY_STRESS_SKIPPED",
            "Moisture-stress analysis is only performed for Paddy fields.",
            "skipped",
        )

    # --- Gate 1: Stage must be available -------------------------------------
    stage_status = stage.get("status")
    stage_label = stage.get("stage") or ""
    stage_evidence = stage.get("evidence") or ""
    if stage_status not in ("completed",):
        return _gate_failure(
            "STAGE_UNAVAILABLE_FOR_STRESS",
            "Moisture-stress analysis requires a provisional growth-stage estimate.",
        )

    # Maturity / harvest: crop is drying naturally — not water stress
    if "Maturity" in stage_label or "Harvest" in stage_label:
        return _gate_failure(
            "STAGE_MATURITY_STRESS_SKIPPED",
            "Field is at maturity or harvest. Natural senescence is not water stress.",
            "skipped",
        )

    # --- Parse cycle start ---------------------------------------------------
    cycle_start_raw = stage.get("cycle_start")
    cycle_start: pd.Timestamp | None = None
    if cycle_start_raw:
        try:
            cycle_start = pd.Timestamp(cycle_start_raw)
        except Exception:
            pass

    # --- S2 optical data preparation ----------------------------------------
    s2_raw = _to_frame(observations, "S2")
    if not s2_raw.empty:
        raw_latest_cloud = pd.to_numeric(
            pd.Series([s2_raw.iloc[-1].get("scene_cloud_percentage")]), errors="coerce"
        ).iloc[0]
        if pd.notna(raw_latest_cloud) and float(raw_latest_cloud) >= 80:
            return _gate_failure(
                "LATEST_OPTICAL_CLOUD_CONTAMINATED",
                "The latest optical observation is severely cloud-affected and cannot be used for stress assessment.",
            )
    s2 = _clean_s2(s2_raw, cycle_start)

    if s2 is None or len(s2) < 2:
        return _gate_failure(
            "INSUFFICIENT_S2_FOR_STRESS",
            "At least two usable optical observations within the crop cycle are required.",
        )

    # --- S1 radar data preparation ------------------------------------------
    preferred_pass = stage.get("selected_s1_orbit_pass")
    preferred_orbit = stage.get("selected_s1_orbit_number")
    s1_raw = _to_frame(observations, "S1")
    s1 = _clean_s1(s1_raw, preferred_pass, preferred_orbit, cycle_start)

    # S1 is optional for stress, but we note when it's absent

    # --- Build S2 statistics -------------------------------------------------
    ndmi = s2["NDMI_median"].dropna()
    ndvi = s2["NDVI_median"].dropna()
    ndwi = s2["NDWI_median"].dropna() if "NDWI_median" in s2.columns else pd.Series(dtype=float)

    ndmi_median = float(ndmi.median()) if len(ndmi) >= 2 else np.nan
    ndmi_mad = _mad(ndmi) if len(ndmi) >= 2 else np.nan
    ndvi_median = float(ndvi.median()) if len(ndvi) >= 2 else np.nan
    ndwi_median = float(ndwi.median()) if len(ndwi) >= 2 else np.nan
    ndwi_mad = _mad(ndwi) if len(ndwi) >= 2 else np.nan

    ndvi_cycle_max = float(ndvi.max()) if len(ndvi) >= 1 else np.nan

    latest_ndmi = float(s2.iloc[-1]["NDMI_median"]) if pd.notna(s2.iloc[-1]["NDMI_median"]) else np.nan
    latest_ndvi = float(s2.iloc[-1]["NDVI_median"]) if pd.notna(s2.iloc[-1]["NDVI_median"]) else np.nan
    latest_ndwi = float(s2.iloc[-1]["NDWI_median"]) if "NDWI_median" in s2.columns and pd.notna(s2.iloc[-1]["NDWI_median"]) else np.nan

    prev_ndvi = float(s2.iloc[-2]["NDVI_median"]) if len(s2) >= 2 and pd.notna(s2.iloc[-2]["NDVI_median"]) else np.nan

    ndmi_delta = (latest_ndmi - ndmi_median) if np.isfinite(latest_ndmi) and np.isfinite(ndmi_median) else np.nan
    ndvi_delta = (latest_ndvi - prev_ndvi) if np.isfinite(latest_ndvi) and np.isfinite(prev_ndvi) else np.nan
    ndvi_drop_from_peak = (ndvi_cycle_max - latest_ndvi) if np.isfinite(ndvi_cycle_max) and np.isfinite(latest_ndvi) else np.nan
    ndwi_delta = (latest_ndwi - ndwi_median) if np.isfinite(latest_ndwi) and np.isfinite(ndwi_median) else np.nan

    # --- Build S1 statistics -------------------------------------------------
    vv_delta: float = np.nan
    vh_delta: float = np.nan
    s1_available = s1 is not None and len(s1) >= 2

    if s1_available:
        _coerce(s1, ["VV_median", "VH_median"])
        vv = s1["VV_median"].dropna()
        vh = s1["VH_median"].dropna()
        vv_median = float(vv.median()) if len(vv) >= 2 else np.nan
        vh_median = float(vh.median()) if len(vh) >= 2 else np.nan
        vv_mad = _mad(vv) if len(vv) >= 2 else np.nan
        vh_mad = _mad(vh) if len(vh) >= 2 else np.nan
        latest_vv = float(s1.iloc[-1]["VV_median"]) if pd.notna(s1.iloc[-1]["VV_median"]) else np.nan
        latest_vh = float(s1.iloc[-1]["VH_median"]) if pd.notna(s1.iloc[-1]["VH_median"]) else np.nan
        vv_delta = (latest_vv - vv_median) if np.isfinite(latest_vv) and np.isfinite(vv_median) else np.nan
        vh_delta = (latest_vh - vh_median) if np.isfinite(latest_vh) and np.isfinite(vh_median) else np.nan
    else:
        vv_mad = np.nan
        vh_mad = np.nan

    # --- Persistence: consecutive dates with NDMI below (median - 1.5*MAD) --
    persistence = 0
    if np.isfinite(ndmi_median) and np.isfinite(ndmi_mad) and ndmi_mad > 0:
        threshold_low = ndmi_median - 1.5 * ndmi_mad
        flags = (s2["NDMI_median"].fillna(ndmi_median) < threshold_low).tolist()
        # Count trailing run of True
        for flag in reversed(flags):
            if flag:
                persistence += 1
            else:
                break
    elif np.isfinite(ndmi_median) and np.isfinite(latest_ndmi):
        # MAD is 0 (all same), treat any deviation as not anomalous
        persistence = 0

    # --- Stage context flags -------------------------------------------------
    is_establishment = "Establishment" in stage_label or "Transplanting" in stage_label
    is_low_stage_evidence = stage_evidence.startswith("Low")

    # --- Evidence accumulation -----------------------------------------------
    evidence: list[str] = []
    counter_evidence: list[str] = []
    score = 0.0

    # S2 NDMI vs field baseline
    if np.isfinite(ndmi_delta) and np.isfinite(ndmi_mad):
        if ndmi_mad > 0:
            ndmi_z = -ndmi_delta / (ndmi_mad + 1e-9)  # positive = below baseline
            if ndmi_z > 2.0:
                score += 0.40  # severe
                evidence.append("NDMI is well below the recent field baseline (>2 MAD deviation)")
            elif ndmi_z > 1.0:
                score += 0.25
                evidence.append("NDMI is below the recent field baseline (>1 MAD deviation)")
        else:
            # All same; any drop is meaningful
            if ndmi_delta < -0.05:
                score += 0.15
                evidence.append("NDMI dropped from the previously stable baseline")

    # NDVI decline vs previous observation
    if np.isfinite(ndvi_delta):
        if ndvi_delta < -0.08:
            score += 0.20
            evidence.append(f"NDVI declined sharply from the previous observation ({ndvi_delta:.3f})")
        elif ndvi_delta < -0.04:
            score += 0.10
            evidence.append(f"NDVI declined compared with the previous observation ({ndvi_delta:.3f})")
        elif ndvi_delta > 0.04:
            counter_evidence.append("NDVI is currently rising — consistent with normal crop growth")
            score -= 0.10

    # NDVI drop from cycle maximum
    if np.isfinite(ndvi_drop_from_peak) and ndvi_drop_from_peak > 0.15:
        if "Vegetative" in stage_label or "Reproductive" in stage_label:
            score += 0.10
            evidence.append(f"NDVI has fallen {ndvi_drop_from_peak:.2f} from the cycle maximum")

    # NDWI vs field baseline
    if np.isfinite(ndwi_delta) and np.isfinite(ndwi_mad):
        if ndwi_mad > 0 and (-ndwi_delta / (ndwi_mad + 1e-9)) > 1.0:
            score += 0.10
            evidence.append("NDWI is below the recent field baseline")

    # S1 radar corroboration
    if s1_available and np.isfinite(vv_delta) and np.isfinite(vv_mad):
        vv_z = -vv_delta / (vv_mad + 1e-9)  # lower VV → positive z
        if vv_z > 1.0:
            score += 0.10
            evidence.append("Radar VV response is below the field median (supporting evidence)")
    if s1_available and np.isfinite(vh_delta) and np.isfinite(vh_mad):
        vh_z = -vh_delta / (vh_mad + 1e-9)
        if vh_z > 1.0:
            score += 0.05
            evidence.append("Radar VH response is below the field median (supporting evidence)")

    # Persistence bonus
    if persistence >= 3:
        score += 0.25
        evidence.append(f"Abnormal optical moisture signal persists across {persistence} consecutive observations")
    elif persistence >= 2:
        score += 0.15
        evidence.append(f"Abnormal optical moisture signal persists across {persistence} consecutive observations")
    elif persistence == 1 and score > 0:
        counter_evidence.append("Only one recent optical anomaly is available — persistence not yet confirmed")
        score -= 0.10

    # --- Counter-evidence deductions -----------------------------------------
    if is_establishment:
        counter_evidence.append(
            "Field is in establishment / transplanting stage — flooded or disturbed baseline is normal"
        )
        score -= 0.20

    if is_low_stage_evidence:
        counter_evidence.append("Stage evidence is low — crop-cycle position is uncertain")
        score -= 0.05

    if not s1_available:
        counter_evidence.append("No S1 radar observations are available for corroboration")

    # --- Clamp score ---------------------------------------------------------
    score = float(np.clip(score, 0.0, 1.0))

    # --- Build chart data arrays ---------------------------------------------
    optical_chart = []
    for _, row in s2.iterrows():
        ndmi_val = row["NDMI_median"] if pd.notna(row.get("NDMI_median")) else None
        ndvi_val = row["NDVI_median"] if pd.notna(row.get("NDVI_median")) else None
        ndwi_val = row["NDWI_median"] if "NDWI_median" in s2.columns and pd.notna(row.get("NDWI_median")) else None
        is_anomaly = bool(
            ndmi_val is not None
            and np.isfinite(ndmi_median)
            and np.isfinite(ndmi_mad)
            and ndmi_mad > 0
            and (ndmi_median - float(ndmi_val)) / (ndmi_mad + 1e-9) > 1.0
        )
        optical_chart.append({
            "date": row["date"].date().isoformat(),
            "ndvi": round(float(ndvi_val), 4) if ndvi_val is not None else None,
            "ndmi": round(float(ndmi_val), 4) if ndmi_val is not None else None,
            "ndwi": round(float(ndwi_val), 4) if ndwi_val is not None else None,
            "stress_marker": is_anomaly,
        })

    radar_chart = []
    if s1 is not None and not s1.empty:
        _coerce(s1, ["VV_median", "VH_median", "VV_minus_VH_median"])
        for _, row in s1.iterrows():
            vv_val = row.get("VV_median")
            vh_val = row.get("VH_median")
            diff_val = row.get("VV_minus_VH_median")
            radar_chart.append({
                "date": row["date"].date().isoformat(),
                "vv": round(float(vv_val), 4) if pd.notna(vv_val) else None,
                "vh": round(float(vh_val), 4) if pd.notna(vh_val) else None,
                "vv_minus_vh": round(float(diff_val), 4) if pd.notna(diff_val) else None,
            })

    # --- Final risk label ----------------------------------------------------
    risk_label = _risk_label(score)
    latest_obs_date = s2.iloc[-1]["date"].date().isoformat()

    return {
        "status": "completed",
        "provisional": True,
        "stress_risk": risk_label,
        "stress_score": round(score, 4),
        "latest_observation_date": latest_obs_date,
        "persistence_observations": persistence,
        "stage_context": stage_label or None,
        "stage_evidence": stage_evidence or None,
        "evidence": evidence,
        "counter_evidence": counter_evidence,
        "warning": WARNING,
        "chart_data": {
            "optical": optical_chart,
            "radar": radar_chart,
        },
        "stress_rule_version": STRESS_RULE_VERSION,
    }
