from fastapi import APIRouter

router = APIRouter(
    prefix="/crop",
    tags=["Crop Prediction"]
)

@router.get("/")
def crop_home():
    return {
        "message": "Crop Router Working"
    }