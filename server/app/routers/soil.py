from fastapi import APIRouter

from app.schemas.soil_schema import (
    SoilInput,
    SoilPredictionResponse,
)

from app.services.soil_service import predict_soil

router = APIRouter(
    prefix="/soil",
    tags=["Soil Fertility"],
)


@router.post(
    "/predict",
    response_model=SoilPredictionResponse,
)
def predict(data: SoilInput):
    return predict_soil(data)