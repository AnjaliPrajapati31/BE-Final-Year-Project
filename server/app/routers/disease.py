from fastapi import APIRouter
from fastapi import File
from fastapi import UploadFile

from app.services.disease_service import predict_disease

router = APIRouter(
    prefix="/disease",
    tags=["Disease Prediction"],
)


@router.post("/predict")
def predict(image: UploadFile = File(...)):
    return predict_disease(image)