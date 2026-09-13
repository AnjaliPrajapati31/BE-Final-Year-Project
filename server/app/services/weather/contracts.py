from __future__ import annotations

from datetime import date
from typing import Protocol

from app.services.sickle.geometry import ValidatedGeometry
from app.services.water.contracts import DailyWeather


class WeatherProvider(Protocol):
    name: str
    live_data: bool

    def historical(
        self, geometry: ValidatedGeometry, start: date, end: date, request_id: str
    ) -> list[DailyWeather]: ...

    def forecast(
        self, geometry: ValidatedGeometry, start: date, days: int, request_id: str
    ) -> list[DailyWeather]: ...
