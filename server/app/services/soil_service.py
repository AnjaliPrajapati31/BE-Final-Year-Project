import pandas as pd

from app.core.exceptions import PredictionException
from app.core.model_loader import soil_model
from app.schemas.soil_schema import SoilInput
from app.utils.response import success

LABELS = {
    0: "Low Fertility",
    1: "Medium Fertility",
    2: "High Fertility",
}


def predict_soil(data: SoilInput) -> dict:
    try:
        features = pd.DataFrame(
            [[
                getattr(data, feature)
                for feature in soil_model.feature_names_in_
            ]],
            columns=soil_model.feature_names_in_,
        )

        prediction = int(soil_model.predict(features)[0])

        return success(
            "Prediction Successful",
            {
                "prediction": LABELS.get(prediction, "Unknown"),
            },
        )
    except Exception as exc:
        raise PredictionException(str(exc)) from exc