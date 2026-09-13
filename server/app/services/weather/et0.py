from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import acos, cos, exp, isfinite, log, pi, sin, sqrt, tan

ET0_ALGORITHM_VERSION = "fao56-pm-v1"


@dataclass(frozen=True)
class WeatherVariables:
    date: date
    latitude_deg: float
    elevation_m: float
    tmin_c: float
    tmax_c: float
    wind_speed_10m_ms: float
    solar_radiation_mj_m2_day: float
    pressure_kpa: float | None = None
    dewpoint_c: float | None = None
    relative_humidity_pct: float | None = None


def saturation_vapour_pressure(temperature_c: float) -> float:
    return 0.6108 * exp(17.27 * temperature_c / (temperature_c + 237.3))


def atmospheric_pressure(elevation_m: float) -> float:
    return 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26


def extraterrestrial_radiation(day_of_year: int, latitude_deg: float) -> float:
    latitude = latitude_deg * pi / 180.0
    inverse_distance = 1.0 + 0.033 * cos(2.0 * pi * day_of_year / 365.0)
    solar_declination = 0.409 * sin(2.0 * pi * day_of_year / 365.0 - 1.39)
    sunset_angle = acos(max(-1.0, min(1.0, -tan(latitude) * tan(solar_declination))))
    return (
        24.0 * 60.0 / pi * 0.0820 * inverse_distance
        * (sunset_angle * sin(latitude) * sin(solar_declination)
           + cos(latitude) * cos(solar_declination) * sin(sunset_angle))
    )


def fao56_penman_monteith(values: WeatherVariables) -> float:
    """Calculate daily reference ET0 in mm/day using FAO-56 equation 6."""
    numbers = (
        values.latitude_deg, values.elevation_m, values.tmin_c, values.tmax_c,
        values.wind_speed_10m_ms, values.solar_radiation_mj_m2_day,
    )
    if not all(isfinite(float(item)) for item in numbers):
        raise ValueError("ET0 inputs must be finite")
    if values.tmax_c < values.tmin_c or values.wind_speed_10m_ms < 0 or values.solar_radiation_mj_m2_day < 0:
        raise ValueError("ET0 temperature, wind, or radiation input is invalid")
    if values.dewpoint_c is None and values.relative_humidity_pct is None:
        raise ValueError("ET0 requires dewpoint or relative humidity")

    mean_temperature = (values.tmin_c + values.tmax_c) / 2.0
    es_min = saturation_vapour_pressure(values.tmin_c)
    es_max = saturation_vapour_pressure(values.tmax_c)
    saturation_pressure = (es_min + es_max) / 2.0
    if values.dewpoint_c is not None:
        actual_pressure = saturation_vapour_pressure(values.dewpoint_c)
    else:
        humidity = max(0.0, min(100.0, float(values.relative_humidity_pct)))
        actual_pressure = saturation_pressure * humidity / 100.0

    pressure = values.pressure_kpa or atmospheric_pressure(values.elevation_m)
    psychrometric = 0.000665 * pressure
    slope = 4098.0 * saturation_vapour_pressure(mean_temperature) / (mean_temperature + 237.3) ** 2
    wind_2m = values.wind_speed_10m_ms * 4.87 / log(67.8 * 10.0 - 5.42)

    day_number = values.date.timetuple().tm_yday
    ra = extraterrestrial_radiation(day_number, values.latitude_deg)
    clear_sky = max(1e-9, (0.75 + 2e-5 * values.elevation_m) * ra)
    solar = values.solar_radiation_mj_m2_day
    net_shortwave = (1.0 - 0.23) * solar
    cloud_factor = max(0.05, min(1.0, 1.35 * min(solar / clear_sky, 1.0) - 0.35))
    sigma = 4.903e-9
    net_longwave = (
        sigma * (((values.tmax_c + 273.16) ** 4 + (values.tmin_c + 273.16) ** 4) / 2.0)
        * (0.34 - 0.14 * sqrt(max(0.0, actual_pressure))) * cloud_factor
    )
    net_radiation = net_shortwave - net_longwave
    numerator = (
        0.408 * slope * net_radiation
        + psychrometric * (900.0 / (mean_temperature + 273.0)) * wind_2m
        * max(0.0, saturation_pressure - actual_pressure)
    )
    denominator = slope + psychrometric * (1.0 + 0.34 * wind_2m)
    return max(0.0, numerator / denominator)
