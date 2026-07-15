from fastapi import APIRouter

router = APIRouter(
    prefix="/disease",
    tags=["Disease Detection"]
)

@router.get("/")
def disease_home():
    return {
        "message": "Disease Router Working"
    }