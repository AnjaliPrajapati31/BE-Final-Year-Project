from datetime import date

import pytest

from app.services.weather.et0 import WeatherVariables, fao56_penman_monteith
from app.services.weather.earth_engine import (
    EarthEngineWeatherProvider,
    aggregate_gfs_rows,
    select_gfs_historical_bridge,
)
from app.services.water.contracts import DailyWeather


def test_fao56_reference_example_is_reproducible():
    values = WeatherVariables(
        date=date(2025, 7, 15), latitude_deg=10.8, elevation_m=5,
        tmin_c=24, tmax_c=32, dewpoint_c=22,
        wind_speed_10m_ms=3.0, solar_radiation_mj_m2_day=20,
        pressure_kpa=101.2,
    )
    assert fao56_penman_monteith(values) == pytest.approx(4.97533, abs=1e-5)


def test_et0_requires_humidity_and_rejects_bad_ranges():
    base = dict(
        date=date(2025, 7, 15), latitude_deg=10.8, elevation_m=5,
        tmin_c=24, tmax_c=32, wind_speed_10m_ms=3,
        solar_radiation_mj_m2_day=20,
    )
    with pytest.raises(ValueError, match="dewpoint"):
        fao56_penman_monteith(WeatherVariables(**base))
    with pytest.raises(ValueError, match="invalid"):
        fao56_penman_monteith(WeatherVariables(**{**base, "tmin_c": 35}, relative_humidity_pct=70))


def test_relative_humidity_path_returns_nonnegative_et0():
    values = WeatherVariables(
        date=date(2025, 12, 1), latitude_deg=10.8, elevation_m=5,
        tmin_c=21, tmax_c=28, relative_humidity_pct=80,
        wind_speed_10m_ms=1.5, solar_radiation_mj_m2_day=12,
    )
    assert fao56_penman_monteith(values) > 0


def test_gfs_aggregation_does_not_double_count_overlapping_steps():
    rows = []
    for hour in (1, 3, 6, 12, 18, 24):
        rows.append({
            "date": "2025-07-15", "forecast_hours": hour,
            "temperature_2m_above_ground": 28 + hour / 24,
            "relative_humidity_2m_above_ground": 70,
            "u_component_of_wind_10m_above_ground": 2,
            "v_component_of_wind_10m_above_ground": 1,
            "total_precipitation_surface": 100 if hour in (1, 3) else 2,
            "downward_shortwave_radiation_flux": 200,
            "creation_time": 1_752_537_600_000,
        })
    result = aggregate_gfs_rows(rows, latitude_deg=10.8, start=date(2025, 7, 15), days=1)
    assert len(result) == 1
    assert result[0].rainfall_mm == 8
    assert result[0].model_creation_time is not None
    assert result[0].raw_variables["forecast_hours"] == [6, 12, 18, 24]
    assert result[0].raw_variables["precipitation_6h_mm"] == [2, 2, 2, 2]
    assert result[0].spatial_resolution_m == 27830


def test_weather_cache_key_and_round_trip_include_source_versions(tmp_path):
    satellite = type("Satellite", (), {"cache_root": tmp_path, "cache_ttl": 60})()
    provider = EarthEngineWeatherProvider(satellite)
    key = {"geometry_hash": "abc", "source": "GPM+ERA5", "version": "fao56-pm-v1"}
    expected = [DailyWeather(date(2025, 7, 15), 3.5, 4.2, source="fixture", quality="checked")]
    provider._write_cache(key, expected)
    assert provider._read_cache(key) == expected
    assert provider._read_cache({**key, "version": "different"}) is None


def test_historical_bridge_prefers_gpm_rain_and_marks_gfs_meteorology():
    rows = [{
        "date": "2025-07-15", "forecast_hours": hour,
        "temperature_2m_above_ground": 28,
        "relative_humidity_2m_above_ground": 70,
        "u_component_of_wind_10m_above_ground": 2,
        "v_component_of_wind_10m_above_ground": 1,
        "total_precipitation_surface": 2,
        "downward_shortwave_radiation_flux": 200,
        "creation_time": 1_752_537_600_000,
    } for hour in (6, 12, 18, 24)]
    result = select_gfs_historical_bridge(
        rows, latitude_deg=10.8, start=date(2025, 7, 15), days=1,
        rainfall_by_date={"2025-07-15": 3.5},
    )
    assert len(result) == 1
    assert result[0].kind == "historical"
    assert result[0].rainfall_mm == 3.5
    assert result[0].raw_variables["rainfall_source"] == "NASA/GPM_L3/IMERG_V07"
