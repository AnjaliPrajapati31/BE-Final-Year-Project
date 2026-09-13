from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GeometryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[Any]
    crs: Any | None = None


class FieldAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    geometry: GeometryInput
    year: int = Field(default=2025, ge=2017, le=2100)
    season: Literal["june_october"] = "june_october"
    sowing_date_hint: date | None = None
    transplanting_date_hint: date | None = None
    generate_artifacts: bool = False

    @field_validator("year")
    @classmethod
    def supported_year(cls, value: int) -> int:
        if value < 2025 or value > date.today().year:
            raise ValueError("Analysis supports the frozen 2025 season through the current year; future seasons are unavailable.")
        return value

    @model_validator(mode="after")
    def validate_cycle_hints(self):
        hints = [item for item in (self.sowing_date_hint, self.transplanting_date_hint) if item is not None]
        if any(item.year != self.year for item in hints):
            raise ValueError("cycle-date hints must fall within the analysis year")
        if any(item > date.today() for item in hints):
            raise ValueError("future cycle-date hints are unavailable")
        if self.sowing_date_hint and self.transplanting_date_hint and self.transplanting_date_hint < self.sowing_date_hint:
            raise ValueError("transplanting date cannot precede sowing date")
        return self


class AnalysisHistoryPage(BaseModel):
    items: list[dict[str, Any]]
    limit: int
    offset: int
