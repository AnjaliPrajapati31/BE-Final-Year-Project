from pydantic import BaseModel, Field


class SoilInput(BaseModel):
    N: float = Field(..., gt=0)
    P: float = Field(..., gt=0)
    K: float = Field(..., gt=0)

    pH: float = Field(..., ge=0, le=14)

    EC: float
    OC: float
    S: float
    Zn: float
    Fe: float
    Cu: float
    Mn: float
    B: float


class SoilPredictionResponse(BaseModel):
    prediction: str