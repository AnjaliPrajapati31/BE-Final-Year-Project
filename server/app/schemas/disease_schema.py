from pydantic import BaseModel


class DiseasePredictionData(BaseModel):
    prediction: str


class DiseasePredictionResponse(BaseModel):
    success: bool
    message: str
    data: DiseasePredictionData | None = None
