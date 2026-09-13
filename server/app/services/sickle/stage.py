from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .contracts import DetailedObservation

STAGE_RULE_VERSION = "provisional-cauvery-v1"
WARNING = (
    "This is a provisional rule-based growth-stage estimate. It has not been "
    "independently validated for this field. A latest observed maximum is not "
    "a confirmed vegetation peak unless a later decline is observed."
)


def skipped_non_paddy() -> dict[str, Any]:
    return {"status": "skipped", "reason_code": "NON_PADDY_STAGE_SKIPPED", "provisional": True, "stage": None, "peak_confirmed": False, "warning": None}


def unavailable(reason_code: str, warning: str) -> dict[str, Any]:
    return {"status": "insufficient_data", "reason_code": reason_code, "provisional": True, "stage": None, "peak_confirmed": False, "warning": warning}


def _frame(observations: list[DetailedObservation], sensor: str) -> pd.DataFrame:
    rows = [{"date": item.date, **item.values, "source_image_id": item.source_image_id} for item in observations if item.sensor == sensor]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame.dropna(subset=["date"])


def _number(frame: pd.DataFrame, names: list[str]) -> None:
    for name in names:
        if name not in frame:
            frame[name] = np.nan
        frame[name] = pd.to_numeric(frame[name], errors="coerce")


def _clean_s2(frame: pd.DataFrame) -> tuple[pd.DataFrame, float] | None:
    if frame.empty or "NDVI_median" not in frame:
        return None
    _number(frame, ["NDVI_median", "NDMI_median", "NDWI_median", "valid_pixel_count", "NDVI_count"])
    if frame["valid_pixel_count"].isna().all():
        frame["valid_pixel_count"] = frame["NDVI_count"]
    frame = frame.dropna(subset=["NDVI_median", "NDMI_median", "valid_pixel_count"])
    frame = frame[(frame["valid_pixel_count"] > 0) & frame["NDVI_median"].between(-1, 1) & frame["NDMI_median"].between(-1, 1)]
    if frame.empty:
        return None
    maximum = float(frame["valid_pixel_count"].max())
    frame["valid_pixel_fraction"] = frame["valid_pixel_count"] / maximum
    selected = None
    threshold_used = 0.0
    for threshold in (0.80, 0.60, 0.45, 0.30):
        candidate = frame[frame["valid_pixel_fraction"] >= threshold]
        if len(candidate) >= 5:
            selected, threshold_used = candidate, threshold
            break
    if selected is None:
        return None
    numeric = [name for name in selected.select_dtypes(include=[np.number]).columns]
    cleaned = selected.groupby("date", as_index=False)[numeric].median().sort_values("date")
    cleaned["NDVI_smooth"] = cleaned["NDVI_median"].rolling(3, center=True, min_periods=1).median()
    cleaned["NDMI_smooth"] = cleaned["NDMI_median"].rolling(3, center=True, min_periods=1).median()
    return cleaned, threshold_used


def _clean_s1(frame: pd.DataFrame) -> tuple[pd.DataFrame, str | None, int | None]:
    if frame.empty:
        return frame, None, None
    rename = {
        "orbitProperties_pass": "orbit_pass",
        "relativeOrbitNumber_start": "orbit_number",
        "relative_orbit_number": "orbit_number",
    }
    frame = frame.rename(columns=rename)
    _number(frame, ["VV_median", "VH_median", "VV_minus_VH_median", "valid_pixel_count", "VV_count", "orbit_number"])
    if frame["valid_pixel_count"].isna().all():
        frame["valid_pixel_count"] = frame["VV_count"]
    if "orbit_pass" not in frame:
        frame["orbit_pass"] = None
    frame = frame.dropna(subset=["VV_median", "VH_median", "valid_pixel_count"])
    frame = frame[frame["valid_pixel_count"] > 0]
    if frame.empty:
        return frame, None, None
    counts = (frame.groupby(["orbit_pass", "orbit_number"], dropna=False).size().reset_index(name="count").sort_values(["count", "orbit_pass", "orbit_number"], ascending=[False, True, True], na_position="last"))
    dominant = counts.iloc[0]
    pass_value = None if pd.isna(dominant["orbit_pass"]) else str(dominant["orbit_pass"])
    orbit_value = None if pd.isna(dominant["orbit_number"]) else int(dominant["orbit_number"])
    selected = frame
    if pass_value is not None:
        selected = selected[selected["orbit_pass"].astype(str) == pass_value]
    if orbit_value is not None:
        selected = selected[pd.to_numeric(selected["orbit_number"], errors="coerce") == orbit_value]
    numeric = [name for name in selected.select_dtypes(include=[np.number]).columns]
    return selected.groupby("date", as_index=False)[numeric].median().sort_values("date"), pass_value, orbit_value


def estimate_stage(observations: list[DetailedObservation]) -> dict[str, Any]:
    s2_result = _clean_s2(_frame(observations, "S2"))
    if s2_result is None:
        return unavailable("INSUFFICIENT_STAGE_OBSERVATIONS", "At least five usable optical observations are required.")
    s2, threshold = s2_result
    if len(s2) < 5:
        return unavailable("INSUFFICIENT_STAGE_OBSERVATIONS", "At least five usable optical observations are required.")
    gaps = s2["date"].diff().dt.days.fillna(0)
    s2["segment"] = (gaps > 30).cumsum()
    eligible = []
    for segment_id, segment in s2.groupby("segment"):
        span = int((segment["date"].max() - segment["date"].min()).days)
        if len(segment) >= 4 and span >= 30:
            eligible.append((segment["date"].max(), segment_id, segment.copy()))
    if not eligible:
        return unavailable("NO_CONTINUOUS_STAGE_SEGMENT", "No optical segment has four dates spanning at least 30 days.")
    _, segment_id, segment = max(eligible, key=lambda item: (item[0], item[1]))
    segment = segment.set_index("date").sort_index()
    daily_index = pd.date_range(segment.index.min(), segment.index.max(), freq="D")
    daily = segment[["NDVI_median", "NDMI_median"]].reindex(daily_index).interpolate(method="time", limit_direction="both")
    daily["NDVI_smooth"] = daily["NDVI_median"].rolling(11, center=True, min_periods=3).median()
    latest_date = daily.index.max()
    window = daily.loc[max(daily.index.min(), latest_date - pd.Timedelta(days=120)):].dropna(subset=["NDVI_smooth"])
    trough_date = window["NDVI_smooth"].idxmin()
    after_trough = window.loc[trough_date:]
    peak_date = after_trough["NDVI_smooth"].idxmax()
    rise = float(after_trough.loc[peak_date, "NDVI_smooth"] - after_trough.loc[trough_date, "NDVI_smooth"])
    if rise < 0.25:
        return unavailable("NO_PLAUSIBLE_VEGETATION_RISE", "No NDVI rise of at least 0.25 was detected.")
    crossings = after_trough[after_trough["NDVI_smooth"] >= 0.25]
    cycle_start = crossings.index[0] if not crossings.empty else trough_date
    current = s2[s2["date"] >= cycle_start].sort_values("date")
    if current.empty:
        return unavailable("LOW_STAGE_EVIDENCE", "No observation follows the provisional cycle start.")
    maximum_row = current.loc[current["NDVI_median"].idxmax()]
    later = current[current["date"] > maximum_row["date"]]
    peak_confirmed = bool(not later.empty and float(maximum_row["NDVI_median"] - later["NDVI_median"].min()) >= 0.15)
    latest = current.iloc[-1]
    days_after = int((latest["date"] - cycle_start).days)
    ndvi = float(latest["NDVI_median"])
    if days_after < 0:
        stage = "Previous crop / field transition"
    elif days_after <= 12 and ndvi < 0.45:
        stage = "Establishment / Transplanting"
    elif days_after <= 45:
        stage = "Vegetative / Tillering"
    elif days_after <= 80:
        stage = "Reproductive / Grain formation"
    elif peak_confirmed and latest["date"] > maximum_row["date"]:
        stage = "Maturity / Harvest"
    else:
        stage = "Late reproductive / stage uncertain"
    span = int((current["date"].max() - current["date"].min()).days)
    if len(current) >= 6 and span >= 50 and peak_confirmed:
        evidence = "Moderate provisional evidence"
    elif len(current) >= 4 and span >= 30:
        evidence = "Low-to-moderate provisional evidence"
    else:
        evidence = "Low provisional evidence"
    s1, orbit_pass, orbit_number = _clean_s1(_frame(observations, "S1"))
    return {
        "status": "completed", "reason_code": "LOW_STAGE_EVIDENCE" if evidence.startswith("Low") else None,
        "provisional": True, "stage": stage, "evidence": evidence,
        "cycle_start": cycle_start.date().isoformat(), "latest_observation": latest["date"].date().isoformat(),
        "current_cycle_count": int(len(current)), "current_cycle_span_days": span,
        "latest_ndvi": ndvi, "latest_ndmi": None if pd.isna(latest["NDMI_median"]) else float(latest["NDMI_median"]),
        "peak_confirmed": peak_confirmed,
        "maximum_interpretation": "Vegetation peak followed by decline" if peak_confirmed else "Latest observed maximum; true peak not confirmed",
        "selected_s1_orbit_pass": orbit_pass, "selected_s1_orbit_number": orbit_number,
        "clean_s1_observation_count": int(len(s1)), "clean_s2_observation_count": int(len(s2)),
        "minimum_s2_valid_fraction_used": threshold, "selected_segment": int(segment_id), "warning": WARNING,
        "timeline": [{"date": row.date.date().isoformat(), "ndvi": float(row.NDVI_median), "ndmi": None if pd.isna(row.NDMI_median) else float(row.NDMI_median)} for row in s2.itertuples()],
    }
