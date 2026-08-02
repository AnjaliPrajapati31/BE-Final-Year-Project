def build_charts(crop: dict, stage: dict) -> dict:
    return {
        "crop_probabilities": [
            {"label": "Paddy", "value": crop["paddy_probability"]},
            {"label": "Non-Paddy", "value": crop["non_paddy_probability"]},
        ],
        "stage_timeline": stage.get("timeline", []),
    }
