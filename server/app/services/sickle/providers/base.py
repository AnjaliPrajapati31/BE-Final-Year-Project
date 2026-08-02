from __future__ import annotations

from typing import Protocol

from ..contracts import CropInputs, DetailedObservation
from ..geometry import ValidatedGeometry


class SatelliteProvider(Protocol):
    name: str
    live_data: bool

    def crop_inputs(self, geometry: ValidatedGeometry, year: int, request_id: str) -> CropInputs: ...

    def detailed_series(self, geometry: ValidatedGeometry, year: int, request_id: str) -> list[DetailedObservation]: ...

    def readiness(self) -> dict: ...
