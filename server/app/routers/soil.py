from fastapi import APIRouter

router = APIRouter(
    prefix="/soil",
    tags=["Soil Analysis"]
)

@router.get("/")
def soil_home():
    return {
        "message": "Soil Router Working"
    }