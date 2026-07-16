import joblib
from tensorflow import keras

from app.config import MODEL_DIR

soil_model = joblib.load(
    MODEL_DIR / "soilfertility.pkl"
)

disease_model = keras.models.load_model(
    MODEL_DIR / "disease.keras"
)

crop_model = None