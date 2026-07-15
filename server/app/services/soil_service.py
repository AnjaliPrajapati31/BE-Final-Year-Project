import joblib
import pandas as pd
from pathlib import Path

from app.schemas.soil_schema import SoilInput

MODEL_PATH = Path("ml_models") / "soilfertility.pkl"

soil_model = joblib.load(MODEL_PATH)

LABELS = {
    0: "Low Fertility",
    1: "Medium Fertility",
    2: "High Fertility",
}


def predict_soil(data: SoilInput) -> dict:
    features = pd.DataFrame(
        [[
            getattr(data, feature)
            for feature in soil_model.feature_names_in_
        ]],
        columns=soil_model.feature_names_in_,
    )

    prediction = soil_model.predict(features)[0]

    return {
        "prediction": LABELS[int(prediction)]
    }