from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from math import hypot
import os
from pathlib import Path
import time

from shapely.geometry import mapping

from app.core.exceptions import DomainError
from app.services.sickle.geometry import ValidatedGeometry
from app.services.water.contracts import DailyWeather

from .et0 import ET0_ALGORITHM_VERSION, WeatherVariables, fao56_penman_monteith

HISTORICAL_SOURCES = ("NASA/GPM_L3/IMERG_V07", "ECMWF/ERA5_LAND/DAILY_AGGR")
FORECAST_SOURCE = "NOAA/GFS0P25"


def aggregate_gfs_rows(rows: list[dict], *, latitude_deg: float, start: date, days: int, elevation_m: float = 0.0) -> list[DailyWeather]:
    """Aggregate only disjoint six-hour GFS steps into local-calendar daily values."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        hours = int(row.get("forecast_hours") or 0)
        if row.get("date") and hours > 0 and hours % 6 == 0:
            grouped[row["date"]].append(row)
    output: list[DailyWeather] = []
    for day_text in sorted(grouped):
        day_rows = grouped[day_text]
        if len(day_rows) < 3:
            continue
        temperatures = [float(row["temperature_2m_above_ground"]) for row in day_rows]
        humidity = sum(float(row["relative_humidity_2m_above_ground"]) for row in day_rows) / len(day_rows)
        wind = sum(hypot(float(row["u_component_of_wind_10m_above_ground"]), float(row["v_component_of_wind_10m_above_ground"])) for row in day_rows) / len(day_rows)
        radiation = sum(max(0.0, float(row["downward_shortwave_radiation_flux"])) * 21600 / 1_000_000 for row in day_rows)
        forecast_date = date.fromisoformat(day_text)
        creation_value = day_rows[0].get("creation_time")
        creation_time = None
        if isinstance(creation_value, (int, float)):
            creation_time = datetime.fromtimestamp(float(creation_value) / 1000.0, tz=timezone.utc)
            age_hours = max(0.0, (datetime.now(timezone.utc) - creation_time).total_seconds() / 3600.0)
            run_quality = (
                f"model_creation_time={creation_time.isoformat()};forecast_age_hours={age_hours:.1f};"
                f"forecast_stale={'true' if age_hours > 18 else 'false'}"
            )
        else:
            run_quality = "model_creation_time=unknown;forecast_age_hours=unknown;forecast_stale=true"
        et0 = fao56_penman_monteith(WeatherVariables(
            forecast_date, latitude_deg, elevation_m, min(temperatures), max(temperatures), wind,
            radiation, relative_humidity_pct=humidity,
        ))
        output.append(DailyWeather(
            date=forecast_date,
            rainfall_mm=sum(max(0.0, float(row["total_precipitation_surface"])) for row in day_rows),
            et0_mm=et0, kind="forecast", source=FORECAST_SOURCE,
            quality="coarse_model_forecast;6_hour_steps;" + ET0_ALGORITHM_VERSION + ";" + run_quality,
            raw_variables={
                "temperature_min_c": min(temperatures), "temperature_max_c": max(temperatures),
                "relative_humidity_pct": humidity, "wind_speed_10m_ms": wind,
                "solar_radiation_mj_m2_day": radiation,
                "precipitation_6h_mm": [max(0.0, float(row["total_precipitation_surface"])) for row in day_rows],
                "forecast_hours": [int(row["forecast_hours"]) for row in day_rows],
                "elevation_m": elevation_m,
            },
            model_creation_time=creation_time, spatial_resolution_m=27830,
        ))
    return [row for row in output if row.date >= start][:days]


def select_gfs_historical_bridge(
    rows: list[dict], *, latitude_deg: float, start: date, days: int,
    rainfall_by_date: dict[str, float], elevation_m: float = 0.0,
) -> list[DailyWeather]:
    """Choose one complete, short-range GFS run per missing local day."""
    by_creation: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        creation = row.get("creation_time")
        if isinstance(creation, (int, float)):
            by_creation[int(creation)].append(row)
    candidates: dict[date, DailyWeather] = {}
    for creation, run_rows in by_creation.items():
        for item in aggregate_gfs_rows(run_rows, latitude_deg=latitude_deg, start=start, days=days, elevation_m=elevation_m):
            if len(item.raw_variables.get("forecast_hours", [])) != 4:
                continue
            previous = candidates.get(item.date)
            if previous is None or (previous.model_creation_time or datetime.min.replace(tzinfo=timezone.utc)) < item.model_creation_time:
                rainfall = rainfall_by_date.get(item.date.isoformat(), item.rainfall_mm)
                candidates[item.date] = DailyWeather(
                    date=item.date, rainfall_mm=rainfall, et0_mm=item.et0_mm, kind="historical",
                    source=(HISTORICAL_SOURCES[0] + "+" + FORECAST_SOURCE
                            if item.date.isoformat() in rainfall_by_date else FORECAST_SOURCE),
                    quality="near_real_time_gfs_bridge;short_range_6_hour_steps;" + ET0_ALGORITHM_VERSION,
                    raw_variables={**item.raw_variables, "rainfall_source": (
                        HISTORICAL_SOURCES[0] if item.date.isoformat() in rainfall_by_date else FORECAST_SOURCE
                    )},
                    model_creation_time=item.model_creation_time,
                    retrieved_at=item.retrieved_at,
                    spatial_resolution_m=item.spatial_resolution_m,
                )
    return [candidates[current] for current in (start + timedelta(days=index) for index in range(days)) if current in candidates]


class EarthEngineWeatherProvider:
    """Polygon weather adapter. Values are coarse estimates, never gauge observations."""

    name = "earth_engine_weather"
    live_data = True

    def __init__(self, satellite_provider):
        self.satellite_provider = satellite_provider
        self.cache_root = Path(satellite_provider.cache_root) / "weather"
        self.cache_ttl = satellite_provider.cache_ttl

    def _cache_path(self, payload: dict) -> Path:
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        return self.cache_root / f"{digest}.json"

    def _read_cache(self, payload: dict, ttl: int | None = None) -> list[DailyWeather] | None:
        path = self._cache_path(payload)
        if not path.is_file() or time.time() - path.stat().st_mtime > (ttl or self.cache_ttl):
            return None
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
            return [DailyWeather(
                date=date.fromisoformat(row["date"]), rainfall_mm=row["rainfall_mm"], et0_mm=row["et0_mm"],
                kind=row["kind"], source=row["source"], quality=row["quality"],
                raw_variables=row.get("raw_variables", {}),
                model_creation_time=(datetime.fromisoformat(row["model_creation_time"]) if row.get("model_creation_time") else None),
                retrieved_at=(datetime.fromisoformat(row["retrieved_at"]) if row.get("retrieved_at") else datetime.now(timezone.utc)),
                spatial_resolution_m=row.get("spatial_resolution_m"),
            ) for row in values]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _write_cache(self, payload: dict, rows: list[DailyWeather]) -> None:
        self.cache_root.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(payload)
        temporary = path.with_suffix(f".{os.getpid()}.tmp")
        data = [{**row.__dict__, "date": row.date.isoformat()} for row in rows]
        temporary.write_text(json.dumps(data, separators=(",", ":"), default=str), encoding="utf-8")
        os.replace(temporary, path)

    def readiness(self) -> dict:
        ready = bool(self.satellite_provider.initialized)
        return {"ready": ready, "provider": self.name, "error": None if ready else self.satellite_provider.error}

    def _ee(self):
        return self.satellite_provider._require_ready()

    @staticmethod
    def _features(info: dict) -> list[dict]:
        return [item.get("properties", {}) for item in info.get("features", [])]

    def _historical_gfs_bridge(
        self, geometry: ValidatedGeometry, start: date, end: date, request_id: str,
        rainfall_by_date: dict[str, float], elevation_m: float,
    ) -> list[DailyWeather]:
        ee = self._ee()
        region = ee.Geometry(mapping(geometry.geometry))
        location = region.centroid(1)
        collection = (ee.ImageCollection(FORECAST_SOURCE).filterBounds(region)
                      .filterDate(ee.Date(start.isoformat()).advance(-1, "day"),
                                  ee.Date(end.isoformat()).advance(1, "day"))
                      .filter(ee.Filter.inList("forecast_hours", [6, 12, 18, 24])))

        def feature(image):
            values = image.select([
                "temperature_2m_above_ground", "relative_humidity_2m_above_ground",
                "u_component_of_wind_10m_above_ground", "v_component_of_wind_10m_above_ground",
                "total_precipitation_surface", "downward_shortwave_radiation_flux",
            ]).reduceRegion(reducer=ee.Reducer.first(), geometry=location, scale=25000, maxPixels=100000)
            local_time = ee.Date(image.get("forecast_time")).advance(330, "minute")
            return ee.Feature(None, values).set({
                "date": local_time.format("YYYY-MM-dd"),
                "forecast_hours": image.get("forecast_hours"),
                "creation_time": image.get("creation_time"),
            })

        try:
            with ee.data.workloadTagContext(request_id):
                info = collection.map(feature).getInfo()
        except Exception as exc:
            raise DomainError("GFS_HISTORY_BRIDGE_UNAVAILABLE", "Recent GFS bridge data could not be retrieved.", 503) from exc
        return select_gfs_historical_bridge(
            self._features(info), latitude_deg=geometry.geometry.centroid.y,
            start=start, days=(end - start).days + 1,
            rainfall_by_date=rainfall_by_date, elevation_m=elevation_m,
        )

    def historical(self, geometry: ValidatedGeometry, start: date, end: date, request_id: str) -> list[DailyWeather]:
        if end < start:
            raise ValueError("historical weather end date precedes start date")
        cache_key = {
            "mode": "historical", "geometry_hash": geometry.geometry_hash,
            "start": start, "end": end, "sources": HISTORICAL_SOURCES,
            "et0_algorithm": ET0_ALGORITHM_VERSION, "provider_contract": "weather-v2",
        }
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached
        ee = self._ee()
        region = ee.Geometry(mapping(geometry.geometry))
        location = region.centroid(1)
        centroid = geometry.geometry.centroid
        dates = ee.List.sequence(0, (end - start).days)
        elevation = ee.Image("USGS/SRTMGL1_003").reduceRegion(
            reducer=ee.Reducer.first(), geometry=location, scale=1000, maxPixels=100000
        ).get("elevation")

        def daily(offset):
            day = ee.Date(start.isoformat()).advance(offset, "day")
            next_day = day.advance(1, "day")
            # IMERG precipitation is a half-hourly rate in mm/hour.
            rain_collection = ee.ImageCollection(HISTORICAL_SOURCES[0]).filterBounds(region).filterDate(day, next_day).select("precipitation")
            masked_rain = ee.Image.constant(0).rename("rainfall_mm").updateMask(ee.Image.constant(0))
            rain = ee.Image(ee.Algorithms.If(
                rain_collection.size().gt(0), rain_collection.sum().multiply(0.5).rename("rainfall_mm"), masked_rain,
            ))
            era_bands = ["temperature_2m_min", "temperature_2m_max", "dewpoint_temperature_2m",
                "u_component_of_wind_10m", "v_component_of_wind_10m",
                "surface_pressure", "surface_solar_radiation_downwards_sum"]
            era_collection = ee.ImageCollection(HISTORICAL_SOURCES[1]).filterBounds(region).filterDate(day, next_day)
            masked_era = ee.Image.constant([0] * len(era_bands)).rename(era_bands).updateMask(ee.Image.constant(0))
            era = ee.Image(ee.Algorithms.If(era_collection.size().gt(0), era_collection.first(), masked_era))
            image = rain.addBands(era.select(era_bands))
            values = image.reduceRegion(
                reducer=ee.Reducer.first(), geometry=location, scale=10000, maxPixels=100000
            )
            return ee.Feature(None, values).set({"date": day.format("YYYY-MM-dd"), "elevation_m": elevation})

        try:
            with ee.data.workloadTagContext(request_id):
                info = ee.FeatureCollection(dates.map(daily)).getInfo()
        except Exception as exc:
            raise DomainError("HISTORICAL_WEATHER_UNAVAILABLE", "Historical rainfall or ET0 inputs could not be retrieved.", 503) from exc

        feature_rows = self._features(info)
        rainfall_by_date = {
            str(row["date"]): max(0.0, float(row["rainfall_mm"]))
            for row in feature_rows if row.get("date") and row.get("rainfall_mm") is not None
        }
        output: list[DailyWeather] = []
        for row in feature_rows:
            required = ("rainfall_mm", "temperature_2m_min", "temperature_2m_max", "dewpoint_temperature_2m",
                        "u_component_of_wind_10m", "v_component_of_wind_10m", "surface_solar_radiation_downwards_sum")
            if not row.get("date") or any(row.get(key) is None for key in required):
                continue
            observed_date = date.fromisoformat(row["date"])
            variables = WeatherVariables(
                date=observed_date, latitude_deg=centroid.y, elevation_m=float(row.get("elevation_m") or 0),
                tmin_c=float(row["temperature_2m_min"]) - 273.15,
                tmax_c=float(row["temperature_2m_max"]) - 273.15,
                dewpoint_c=float(row["dewpoint_temperature_2m"]) - 273.15,
                wind_speed_10m_ms=hypot(float(row["u_component_of_wind_10m"]), float(row["v_component_of_wind_10m"])),
                pressure_kpa=None if row.get("surface_pressure") is None else float(row["surface_pressure"]) / 1000.0,
                solar_radiation_mj_m2_day=float(row["surface_solar_radiation_downwards_sum"]) / 1_000_000.0,
            )
            output.append(DailyWeather(
                date=observed_date, rainfall_mm=max(0.0, float(row["rainfall_mm"])),
                et0_mm=fao56_penman_monteith(variables), kind="historical",
                source="+".join(HISTORICAL_SOURCES),
                quality="coarse_satellite_rainfall_and_reanalysis;" + ET0_ALGORITHM_VERSION,
                raw_variables={
                    "temperature_min_k": float(row["temperature_2m_min"]),
                    "temperature_max_k": float(row["temperature_2m_max"]),
                    "dewpoint_temperature_k": float(row["dewpoint_temperature_2m"]),
                    "u_wind_10m_ms": float(row["u_component_of_wind_10m"]),
                    "v_wind_10m_ms": float(row["v_component_of_wind_10m"]),
                    "surface_pressure_pa": None if row.get("surface_pressure") is None else float(row["surface_pressure"]),
                    "solar_radiation_j_m2_day": float(row["surface_solar_radiation_downwards_sum"]),
                    "elevation_m": float(row.get("elevation_m") or 0),
                    "rainfall_mm": max(0.0, float(row["rainfall_mm"])),
                },
                spatial_resolution_m=10000,
            ))
        output.sort(key=lambda item: item.date)
        if not output or output[0].date != start:
            raise DomainError("INCOMPLETE_HISTORICAL_WEATHER", "Historical weather is missing the crop-cycle start.", 503)
        for previous, current in zip(output, output[1:]):
            if current.date != previous.date + timedelta(days=1):
                raise DomainError("INCOMPLETE_HISTORICAL_WEATHER", "Historical weather contains an internal missing day.", 503)
        trailing_gap = (end - output[-1].date).days
        if 0 < trailing_gap <= 10:
            bridge_start = output[-1].date + timedelta(days=1)
            try:
                bridge = self._historical_gfs_bridge(
                    geometry, bridge_start, end, request_id, rainfall_by_date,
                    float(feature_rows[0].get("elevation_m") or 0),
                )
                if len(bridge) == trailing_gap and bridge[0].date == bridge_start:
                    output.extend(bridge)
                    trailing_gap = (end - output[-1].date).days
            except DomainError:
                pass
        if trailing_gap > 30:
            raise DomainError("STALE_HISTORICAL_WEATHER", "Historical weather is more than thirty days behind the requested date.", 503)
        self._write_cache(cache_key, output)
        return output

    def forecast(self, geometry: ValidatedGeometry, start: date, days: int, request_id: str) -> list[DailyWeather]:
        if not 1 <= days <= 10:
            raise ValueError("forecast horizon must be between one and ten days")
        ee = self._ee()
        region = ee.Geometry(mapping(geometry.geometry))
        location = region.centroid(1)
        centroid = geometry.geometry.centroid
        collection = (ee.ImageCollection(FORECAST_SOURCE).filterBounds(region)
                      .filterDate(ee.Date(start.isoformat()).advance(-2, "day"),
                                  ee.Date(start.isoformat()).advance(days + 1, "day")))
        try:
            with ee.data.workloadTagContext(request_id):
                complete_runs = collection.filter(ee.Filter.gte("forecast_hours", days * 24))
                latest_creation = complete_runs.aggregate_max("creation_time").getInfo()
        except Exception as exc:
            raise DomainError("FORECAST_WEATHER_UNAVAILABLE", "Latest complete GFS model run could not be selected.", 503) from exc
        if latest_creation is None:
            raise DomainError("FORECAST_WEATHER_UNAVAILABLE", "No complete GFS model run covers the requested horizon.", 503)
        cache_key = {
            "mode": "forecast", "geometry_hash": geometry.geometry_hash, "start": start,
            "days": days, "source": FORECAST_SOURCE, "model_creation_time": latest_creation,
            "et0_algorithm": ET0_ALGORITHM_VERSION, "local_timezone": "Asia/Kolkata",
            "provider_contract": "weather-v2",
        }
        cached = self._read_cache(cache_key, ttl=min(self.cache_ttl, 21600))
        if cached is not None:
            return cached
        # Six-hour forecast steps contain disjoint preceding six-hour precipitation totals.
        selected = (collection.filter(ee.Filter.eq("creation_time", latest_creation))
                    .filter(ee.Filter.gt("forecast_hours", 0))
                    .filter(ee.Filter.inList("forecast_hours", list(range(6, (days + 1) * 24 + 1, 6)))))

        def feature(image):
            forecast_hours = ee.Number(image.get("forecast_hours"))
            values = image.select([
                "temperature_2m_above_ground", "relative_humidity_2m_above_ground",
                "u_component_of_wind_10m_above_ground", "v_component_of_wind_10m_above_ground",
                "total_precipitation_surface", "downward_shortwave_radiation_flux",
            ]).reduceRegion(reducer=ee.Reducer.first(), geometry=location, scale=25000, maxPixels=100000)
            local_time = ee.Date(image.get("forecast_time")).advance(330, "minute")
            return ee.Feature(None, values).set({
                "date": local_time.format("YYYY-MM-dd"), "forecast_hours": forecast_hours,
                "creation_time": image.get("creation_time"),
            })

        try:
            with ee.data.workloadTagContext(request_id):
                info = selected.map(feature).getInfo()
        except Exception as exc:
            raise DomainError("FORECAST_WEATHER_UNAVAILABLE", "Five-day GFS forecast could not be retrieved.", 503) from exc

        desired = aggregate_gfs_rows(self._features(info), latitude_deg=centroid.y, start=start, days=days)
        if not desired:
            raise DomainError("FORECAST_WEATHER_UNAVAILABLE", "GFS returned no usable forecast days.", 503)
        self._write_cache(cache_key, desired)
        return desired
