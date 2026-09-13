from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IrrigationEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_date: date
    amount: float = Field(gt=0)
    unit: Literal["mm", "m3"]
    irrigation_method: str = Field(default="surface", min_length=1, max_length=50)
    application_efficiency: float = Field(default=0.60, gt=0, le=1)
    source: Literal["user", "imported"] = "user"
    client_event_id: str | None = Field(default=None, min_length=1, max_length=100)
    supersedes_event_id: UUID | None = None
    correction_reason: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_event(self):
        if self.event_date > date.today():
            raise ValueError("future irrigation events are not accepted")
        if bool(self.supersedes_event_id) != bool(self.correction_reason):
            raise ValueError("a correction requires both supersedes_event_id and correction_reason")
        return self


class IrrigationEventVoid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=500)


class FieldWaterProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_version: Literal["cauvery-paddy-v1"] = "cauvery-paddy-v1"
    source: Literal["user", "imported", "measured"] = "user"
    field_capacity: float | None = Field(default=None, gt=0, le=1)
    wilting_point: float | None = Field(default=None, ge=0, lt=1)
    root_depth_m: float | None = Field(default=None, gt=0, le=3)
    depletion_fraction: float | None = Field(default=None, gt=0, le=1)
    seepage_percolation_mm_day: float | None = Field(default=None, ge=0, le=30)
    max_ponding_mm: float | None = Field(default=None, ge=0, le=200)
    irrigation_efficiency: float | None = Field(default=None, gt=0, le=1)
    initial_ponded_water_mm: float | None = Field(default=None, ge=0, le=200)
    initial_root_depletion_mm: float | None = Field(default=None, ge=0, le=500)

    @model_validator(mode="after")
    def validate_soil_water(self):
        if self.field_capacity is not None and self.wilting_point is not None and self.wilting_point >= self.field_capacity:
            raise ValueError("wilting_point must be lower than field_capacity")
        return self
