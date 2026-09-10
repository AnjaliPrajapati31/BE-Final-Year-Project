from __future__ import annotations


def build_charts(crop: dict, stage: dict, stress: dict | None = None) -> dict:
    chart_data = stress.get("chart_data", {}) if stress else {}
    return {
        "crop_probabilities": [
            {"label": "Paddy", "value": crop["paddy_probability"]},
            {"label": "Non-Paddy", "value": crop["non_paddy_probability"]},
        ],
        "stage_timeline": stage.get("timeline", []),
        "stress_optical": chart_data.get("optical", []),
        "stress_radar": chart_data.get("radar", []),
    }
