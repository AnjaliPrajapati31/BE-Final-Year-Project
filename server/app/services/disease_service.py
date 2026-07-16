import io
import logging

import numpy as np
from fastapi import UploadFile
from PIL import Image

from app.core.exceptions import PredictionException
from app.core.model_loader import disease_model
from app.utils.image_utils import preprocess_image
from app.utils.response import success

logger = logging.getLogger(__name__)

CLASS_LABELS = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]


def format_label(label: str) -> str:
    """Format disease label by replacing ___ with ' - ' and _ with space."""
    label = label.replace("___", " - ")
    label = label.replace("__", " - ")
    label = label.replace("_", " ")
    return label


def predict_disease(image: UploadFile):
    try:
        image_data = image.file.read()
        pil_image = Image.open(io.BytesIO(image_data))
        processed = preprocess_image(pil_image)
        
        logger.debug(f"Processed image shape: {processed.shape}")
        
        prediction = disease_model.predict(processed, verbose=0)
        logger.debug(f"Model output shape: {prediction.shape}")
        
        confidence_scores = prediction[0]
        
        # Log top 5 predictions with their indices and class names
        top_5_indices = np.argsort(confidence_scores)[-5:][::-1]
        logger.info("\n=== TOP 5 PREDICTIONS ===")
        for idx, class_idx in enumerate(top_5_indices):
            score = confidence_scores[class_idx]
            class_name = CLASS_LABELS[class_idx] if class_idx < len(CLASS_LABELS) else "Unknown"
            logger.info(f"#{idx+1}: Index {class_idx} - {class_name} - Score: {score:.4f}")
        logger.info("========================\n")
        
        class_index = int(np.argmax(confidence_scores))
        max_confidence = float(np.max(confidence_scores))
        confidence = round(max_confidence * 100, 2)
        
        logger.debug(f"Selected: Index {class_index}, Confidence: {confidence}%")
        
        disease_label = CLASS_LABELS[class_index]
        formatted_disease = format_label(disease_label)

        return success(
            "Disease prediction completed",
            {
                "disease": formatted_disease,
                "confidence": confidence,
                "raw_prediction": formatted_disease,
            },
        )
    except Exception as exc:
        logger.error(f"Disease prediction error: {exc}")
        raise PredictionException(f"Disease prediction failed: {str(exc)}") from exc
