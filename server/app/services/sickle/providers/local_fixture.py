from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from app.core.exceptions import DomainError

from ..contracts import CropInputs, DetailedObservation, Grid, ObservationQuality


class LocalFixtureProvider:
    """Known-answer provider for CLI/tests only; never registered in FastAPI state."""

    name = "local_fixture"
    live_data = False
    test_only = True

    def __init__(self, root: Path):
        self.root = root

    def readiness(self) -> dict:
        required = [self.root / "pilot_001_sickle_input.npz", self.root / "pilot_001_s1_detailed.csv", self.root / "pilot_001_s2_detailed.csv"]
        missing = [path.name for path in required if not path.is_file()]
        return {"ready": not missing, "missing": missing, "provider": self.name, "live_data": False}

    def crop_inputs(self, geometry=None, year: int = 2025, request_id: str = "pilot_001") -> CropInputs:
        path = self.root / "pilot_001_sickle_input.npz"
        if not path.is_file():
            raise DomainError("NO_OVERLAPPING_RASTER", "PILOT_001 crop fixture is missing.", 503)
        with np.load(path, allow_pickle=False) as fixture:
            quality = []
            for sensor, months in (("S1", fixture["S1_months"].tolist()), ("S2", fixture["S2_months"].tolist())):
                quality.extend(ObservationQuality(sensor, str(month), 0, True, 0.0) for month in months)
            return CropInputs(
                s1=fixture["S1"].astype(np.float32), s1_dates=fixture["S1_dates"].astype(np.int64), s1_months=fixture["S1_months"].tolist(),
                s2=fixture["S2"].astype(np.float32), s2_dates=fixture["S2_dates"].astype(np.int64), s2_months=fixture["S2_months"].tolist(),
                field_mask=fixture["field_mask"].astype(bool),
                grid=Grid(str(fixture["target_crs"].item()) if "target_crs" in fixture.files else "EPSG:4326", tuple(float(v) for v in fixture["target_transform"])),
                quality=quality, provider=self.name, live_data=False,
            )

    def detailed_series(self, geometry=None, year: int = 2025, request_id: str = "pilot_001") -> list[DetailedObservation]:
        observations = []
        for sensor in ("s1", "s2"):
            path = self.root / f"pilot_001_{sensor}_detailed.csv"
            if not path.is_file():
                raise DomainError("DETAILED_TIMESERIES_UNAVAILABLE", f"PILOT_001 {sensor.upper()} fixture is missing.")
            with path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    observations.append(DetailedObservation(sensor.upper(), row.pop("date"), row))
        return observations
