from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Literal["en", "ta"] = "en"
    regenerate: bool = False


class AnalysisExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1000)
    crop_and_stage: str = Field(min_length=1, max_length=1000)
    water_status: str = Field(min_length=1, max_length=1000)
    irrigation_guidance: str = Field(min_length=1, max_length=1000)
    cautions: list[str] = Field(max_length=8)
