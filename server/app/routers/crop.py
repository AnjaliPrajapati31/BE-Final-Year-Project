from fastapi import APIRouter

from app.services.crop_service import predict_crop

router = APIRouter(
    prefix="/crop",
    tags=["Crop Prediction"],
)


@router.get("/")
def crop_home():
    return predict_crop()