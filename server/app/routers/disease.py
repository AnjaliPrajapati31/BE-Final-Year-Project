from fastapi import APIRouter

from app.services.disease_service import predict_disease

router = APIRouter(
    prefix="/disease",
    tags=["Disease Prediction"],
)


@router.get("/")
def test():
    return predict_disease()