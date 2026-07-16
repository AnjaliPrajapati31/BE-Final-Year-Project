from pydantic import BaseModel


class DiseasePredictionResponse(BaseModel):
    disease: str
