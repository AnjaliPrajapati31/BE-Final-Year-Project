from pydantic import BaseModel


class CropPredictionResponse(BaseModel):
    crop: str
