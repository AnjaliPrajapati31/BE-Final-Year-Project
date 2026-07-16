from fastapi import HTTPException


class PredictionException(HTTPException):
    def __init__(self, detail: str = "Prediction Failed"):
        super().__init__(
            status_code=500,
            detail=detail,
        )
