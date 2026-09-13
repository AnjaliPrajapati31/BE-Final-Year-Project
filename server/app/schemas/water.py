from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

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


class WaterObservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observed_at: datetime
    observation_type: Literal["ponded_depth", "water_table_depth", "volumetric_soil_water"]
    value: float = Field(ge=0)
    unit: Literal["mm", "m3/m3"]
    measurement_depth_m: float | None = Field(default=None, gt=0, le=3)
    method: str = Field(min_length=1, max_length=100)
    source: Literal["user", "imported", "sensor"] = "user"
    reliability: Literal["high", "medium", "low"] = "medium"
    client_observation_id: str | None = Field(default=None, min_length=1, max_length=100)
    supersedes_observation_id: UUID | None = None
    correction_reason: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_observation(self):
        if self.observed_at.tzinfo is None:
            self.observed_at = self.observed_at.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        self.observed_at = self.observed_at.astimezone(timezone.utc)
        if self.observed_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("future water observations are not accepted")
        if self.observation_type in {"ponded_depth", "water_table_depth"}:
            if self.unit != "mm" or self.value > 1000:
                raise ValueError("water depth must use mm and be between 0 and 1000")
            if self.measurement_depth_m is not None:
                raise ValueError("measurement_depth_m is only valid for volumetric soil water")
        else:
            if self.unit != "m3/m3" or self.value > 1:
                raise ValueError("volumetric soil water must use m3/m3 and be between 0 and 1")
            if self.measurement_depth_m is None:
                raise ValueError("measurement_depth_m is required for volumetric soil water")
        if bool(self.supersedes_observation_id) != bool(self.correction_reason):
            raise ValueError("a correction requires both supersedes_observation_id and correction_reason")
        return self


class WaterObservationVoid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=500)


class IrrigationHistoryCoverageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coverage_status: Literal["complete", "partial", "unknown"]
    coverage_start: date | None = None
    coverage_end: date | None = None
    source: Literal["user", "imported", "measured"] = "user"
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_coverage(self):
        if self.coverage_status != "unknown" and (self.coverage_start is None or self.coverage_end is None):
            raise ValueError("complete and partial coverage require start and end dates")
        if self.coverage_start and self.coverage_end and self.coverage_end < self.coverage_start:
            raise ValueError("coverage end cannot precede coverage start")
        if self.coverage_end and self.coverage_end > date.today():
            raise ValueError("irrigation-history coverage cannot extend into the future")
        return self


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
