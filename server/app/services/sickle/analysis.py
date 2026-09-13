from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
import logging
from uuid import UUID, uuid4

from app.core.exceptions import DomainError

from .charts import build_charts
from .crop import PREPROCESSING_VERSION, summarize_crop, validate_crop_inputs
from .geometry import validate_geometry
from .stage import STAGE_RULE_VERSION, estimate_stage, skipped_non_paddy, unavailable
from .stress import STRESS_RULE_VERSION, estimate_stress
from app.services.water.advisory import build_irrigation_advisory
from app.services.water.balance import calculate_paddy_balance
from app.services.water.contracts import DailyWeather, WaterState
from app.services.water.profiles import CAUVERY_PADDY_V1

logger = logging.getLogger(__name__)


def _strip_chart_data(stress: dict | None) -> dict | None:
    """Return the stress dict without chart_data (charts are placed in the charts key)."""
    if stress is None:
        return None
    return {key: value for key, value in stress.items() if key != "chart_data"}


def _module_contract(result: dict, *, evidence_level: str | None = None, rule_version: str | None = None) -> dict:
    warnings = result.get("warnings") or ([result["warning"]] if result.get("warning") else [])
    return {
        "status": result["status"], "provisional": result.get("provisional", False),
        "evidence_level": evidence_level or result.get("evidence_level"),
        "reason_code": result.get("reason_code"), "warnings": warnings,
        "input_sources": result.get("input_sources", []),
        "rule_version": rule_version or result.get("rule_version"),
    }


class AnalysisService:
    def __init__(self, settings, roi, repository, provider, crop_runtime, artifact_writer, weather_provider=None):
        self.settings = settings
        self.roi = roi
        self.repository = repository
        self.provider = provider
        self.crop_runtime = crop_runtime
        self.artifact_writer = artifact_writer
        self.weather_provider = weather_provider

    def _save_module(self, request_id, module: str, result: dict) -> None:
        if hasattr(self.repository, "save_module_run"):
            self.repository.save_module_run(request_id, module, result)

    def analyze(self, command) -> dict:
        request_id = uuid4()
        geometry = validate_geometry(
            command.geometry.model_dump(exclude_none=True), max_vertices=self.settings.FIELD_MAX_VERTICES,
            min_area_m2=self.settings.FIELD_MIN_AREA_M2, max_area_m2=self.settings.FIELD_MAX_AREA_M2,
            max_width_m=self.settings.FIELD_MAX_WIDTH_M, max_height_m=self.settings.FIELD_MAX_HEIGHT_M,
            roi=self.roi,
        )
        try:
            roi_id = self.repository.verify_roi(geometry.geometry_json, geometry.patch_json)
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError("DATABASE_NOT_READY", "Authoritative Cauvery containment is unavailable.", 503) from exc
        run = {
            "request_id": request_id, "provider": self.provider.name, "live_data": self.provider.live_data,
            "cached": False, "year": command.year, "season": command.season,
            "model_name": self.crop_runtime.model_name, "checkpoint_sha256": self.crop_runtime.checkpoint_sha256,
            "preprocessing_version": PREPROCESSING_VERSION, "stage_rule_version": STAGE_RULE_VERSION,
            "stress_rule_version": STRESS_RULE_VERSION,
            "field_pixel_count": geometry.field_pixel_count,
        }
        try:
            self.repository.create_revision_and_run(command.field_id, geometry, roi_id, run)
        except Exception as exc:
            raise DomainError("DATABASE_WRITE_FAILED", "Could not persist the accepted field analysis.", 500) from exc
        try:
            self.repository.set_status(request_id, "fetching_crop_data")
            inputs = self.provider.crop_inputs(geometry, command.year, str(request_id))
            validate_crop_inputs(inputs)
            if int(inputs.field_mask.sum()) != geometry.field_pixel_count:
                raise DomainError("CROP_INFERENCE_FAILED", "Provider grid does not match the validated field mask.", 500)
            self.repository.set_provider_cached(request_id, inputs.cached)
            self.repository.save_crop_quality(request_id, inputs.quality)
            self.repository.set_status(request_id, "running_crop_model")
            probabilities = self.crop_runtime.infer(inputs.s1, inputs.s1_dates, inputs.s2, inputs.s2_dates)
            crop = summarize_crop(probabilities, inputs.field_mask, inputs)
            crop["rejected_months"] = {
                sensor: [quality.month for quality in inputs.quality if quality.sensor == sensor and not quality.accepted]
                for sensor in ("S1", "S2")
            }
            self.repository.save_crop(request_id, crop)
            if hasattr(self.repository, "save_result_payload"):
                self.repository.save_result_payload(request_id, "crop", crop)
            modules = {
                "crop": _module_contract({"status": "completed", "provisional": False, "evidence_level": "medium",
                         "reason_code": None, "warnings": [], "input_sources": [inputs.provider],
                         "rule_version": PREPROCESSING_VERSION})
            }
            self._save_module(request_id, "crop", modules["crop"])
            warnings = [f"Missing usable {sensor} months: {', '.join(months)}" for sensor, months in crop["rejected_months"].items() if months]
            today = date.today()
            if command.year == today.year and today < date(today.year, 11, 1):
                warnings.insert(0, f"In-season experimental result using observations available through {today.isoformat()}; future observations were not fabricated.")
            if crop["class_label"] != "Paddy":
                stage = skipped_non_paddy()
                self.repository.save_stage(request_id, stage)
                modules["growth_stage"] = _module_contract(stage, evidence_level="low", rule_version=STAGE_RULE_VERSION)
                status = "completed"
            else:
                self.repository.set_status(request_id, "fetching_stage_data")
                observations = []
                try:
                    observations = self.provider.detailed_series(geometry, command.year, str(request_id))
                    self.repository.save_observations(request_id, observations, "stage")
                    self.repository.set_status(request_id, "running_stage_rules")
                    stage = estimate_stage(observations)
                except DomainError as exc:
                    stage = unavailable(exc.code if exc.code.startswith(("INSUFFICIENT_", "NO_", "DETAILED_")) else "DETAILED_TIMESERIES_UNAVAILABLE", exc.message)
                except Exception:
                    stage = unavailable("DETAILED_TIMESERIES_UNAVAILABLE", "Detailed Earth Engine time-series retrieval failed.")
                self.repository.save_stage(request_id, stage)
                modules["growth_stage"] = _module_contract(
                    stage, evidence_level="low" if str(stage.get("evidence", "")).startswith("Low") else "medium",
                    rule_version=STAGE_RULE_VERSION,
                )
                if stage["status"] != "completed" or stage.get("reason_code") == "LOW_STAGE_EVIDENCE":
                    warnings.append(stage.get("warning") or "Growth stage is not available.")
                    status = "partial"
                else:
                    status = "completed"
            if hasattr(self.repository, "save_result_payload"):
                self.repository.save_result_payload(request_id, "growth_stage", stage)
            self._save_module(request_id, "growth_stage", modules["growth_stage"])
            # --- Moisture-stress risk (Paddy only, after stage) ---------------
            stress: dict | None = None
            if crop["class_label"] == "Paddy":
                try:
                    self.repository.set_status(request_id, "running_stress_rules")
                    stress = estimate_stress(observations, stage, crop)
                    self.repository.save_stress(request_id, stress)
                    if stress["status"] == "insufficient_data":
                        warnings.append(
                            stress.get("warning") or "Moisture-stress data are insufficient."
                        )
                        if status == "completed":
                            status = "partial"
                except Exception:
                    logger.exception("Stress estimation failed for analysis %s", request_id)
                    stress = {
                        "status": "failed", "reason_code": "STRESS_ESTIMATION_FAILED",
                        "provisional": True, "stress_risk": None, "stress_score": None,
                        "latest_observation_date": None, "persistence_observations": None,
                        "stage_context": stage.get("stage"), "stage_evidence": stage.get("evidence"),
                        "evidence": [], "counter_evidence": [],
                        "warning": "Moisture-stress estimation failed; independent modules may still complete.",
                        "chart_data": {"optical": [], "radar": []},
                        "stress_rule_version": STRESS_RULE_VERSION,
                    }
                    try:
                        self.repository.save_stress(request_id, stress)
                    except Exception:
                        logger.exception("Could not persist failed stress status for analysis %s", request_id)
                    warnings.append(stress["warning"])
                    status = "partial"
            else:
                stress = estimate_stress([], stage, crop)
                if hasattr(self.repository, "save_stress"):
                    self.repository.save_stress(request_id, stress)
            modules["moisture_stress"] = _module_contract(
                stress or {"status": "failed", "reason_code": "STRESS_RESULT_MISSING", "provisional": True},
                evidence_level="low" if not stress or stress.get("status") != "completed" else "medium",
                rule_version=STRESS_RULE_VERSION,
            )
            if hasattr(self.repository, "save_result_payload"):
                self.repository.save_result_payload(request_id, "moisture_stress", _strip_chart_data(stress) if stress else {})
            self._save_module(request_id, "moisture_stress", modules["moisture_stress"])

            weather_result = None
            water_balance = None
            irrigation_advisory = None
            water_chart = []
            if crop["class_label"] != "Paddy":
                for module, reason in (
                    ("weather", "NON_PADDY_WEATHER_SKIPPED"),
                    ("water_balance", "NON_PADDY_WATER_BALANCE_SKIPPED"),
                    ("irrigation_advisory", "NON_PADDY_ADVISORY_SKIPPED"),
                ):
                    modules[module] = {"status": "skipped", "reason_code": reason, "provisional": True,
                                       "evidence_level": "low", "warnings": [], "input_sources": []}
                    self._save_module(request_id, module, modules[module])
            elif stage.get("status") != "completed" or not stage.get("cycle_start"):
                modules["weather"] = {"status": "skipped", "reason_code": "CYCLE_START_UNAVAILABLE", "provisional": True,
                                      "evidence_level": "low", "warnings": [], "input_sources": []}
                modules["water_balance"] = {"status": "insufficient_data", "reason_code": "CYCLE_START_UNAVAILABLE", "provisional": True,
                                            "evidence_level": "low", "warnings": ["A usable crop-cycle start is required."], "input_sources": []}
                modules["irrigation_advisory"] = {"status": "skipped", "reason_code": "WATER_BALANCE_UNAVAILABLE", "provisional": True,
                                                  "evidence_level": "low", "warnings": [], "input_sources": []}
                for module in ("weather", "water_balance", "irrigation_advisory"):
                    self._save_module(request_id, module, modules[module])
                status = "partial"
            elif self.weather_provider is None:
                modules["weather"] = {"status": "failed", "reason_code": "WEATHER_PROVIDER_NOT_CONFIGURED", "provisional": True,
                                      "evidence_level": "low", "warnings": ["Weather provider is unavailable."], "input_sources": []}
                modules["water_balance"] = {"status": "insufficient_data", "reason_code": "HISTORICAL_WEATHER_UNAVAILABLE", "provisional": True,
                                            "evidence_level": "low", "warnings": ["Historical weather is required."], "input_sources": []}
                modules["irrigation_advisory"] = {"status": "skipped", "reason_code": "WATER_BALANCE_UNAVAILABLE", "provisional": True,
                                                  "evidence_level": "low", "warnings": [], "input_sources": []}
                for module in ("weather", "water_balance", "irrigation_advisory"):
                    self._save_module(request_id, module, modules[module])
                warnings.append("Weather provider is unavailable; water balance was not calculated.")
                status = "partial"
            else:
                try:
                    self.repository.set_status(request_id, "fetching_weather")
                    cycle_start_value = command.transplanting_date_hint or command.sowing_date_hint or stage["cycle_start"]
                    cycle_start = cycle_start_value if isinstance(cycle_start_value, date) else date.fromisoformat(str(cycle_start_value))
                    cycle_source = "transplanting_date" if command.transplanting_date_hint else (
                        "sowing_date" if command.sowing_date_hint else "satellite_stage"
                    )
                    end_date = min(date(command.year, 12, 31), date.today())
                    historical = self.weather_provider.historical(geometry, cycle_start, end_date, str(request_id))
                    historical_lag_days = (end_date - historical[-1].date).days
                    forecast = []
                    advisory_forecast = []
                    forecast_warning = None
                    if command.year == date.today().year:
                        try:
                            forecast = self.weather_provider.forecast(geometry, date.today() + timedelta(days=1), 5, str(request_id))
                            advisory_forecast = forecast
                            if len(forecast) < 5:
                                advisory_forecast = []
                                forecast_warning = "Forecast horizon is incomplete; advisory uses current deficit only."
                            elif any("forecast_stale=true" in str(item.quality) for item in forecast):
                                advisory_forecast = []
                                forecast_warning = "Forecast model run is stale; advisory uses current deficit only."
                        except Exception:
                            forecast_warning = "Forecast is unavailable or stale; advisory uses current deficit only."
                    if hasattr(self.repository, "save_weather"):
                        self.repository.save_weather(request_id, historical + forecast)
                    weather_result = {
                        "status": "completed", "provisional": False, "evidence_level": "low", "reason_code": None,
                        "historical_days": len(historical), "forecast_days": len(forecast),
                        "historical": [item.__dict__ for item in historical], "forecast": [item.__dict__ for item in forecast],
                        "historical_as_of_date": historical[-1].date.isoformat(),
                        "historical_lag_days": historical_lag_days,
                        "warnings": ["Rainfall and meteorology are coarse spatial estimates, not field gauge measurements."]
                        + ([f"Historical weather is {historical_lag_days} day(s) behind the requested analysis date."] if historical_lag_days else [])
                        + ([forecast_warning] if forecast_warning else []),
                        "input_sources": sorted({item.source for item in historical + forecast}), "rule_version": "fao56-pm-v1",
                    }
                    if hasattr(self.repository, "save_result_payload"):
                        self.repository.save_result_payload(request_id, "weather", weather_result)
                    modules["weather"] = _module_contract(weather_result)
                    self._save_module(request_id, "weather", modules["weather"])

                    profile = CAUVERY_PADDY_V1
                    stored_profile = self.repository.get_water_profile(command.field_id) if hasattr(self.repository, "get_water_profile") else None
                    initial_state = None
                    initial_state_source = "stage_default"
                    if stored_profile and stored_profile.get("overrides"):
                        overrides = dict(stored_profile["overrides"])
                        initial_ponded = overrides.pop("initial_ponded_water_mm", None)
                        initial_depletion = overrides.pop("initial_root_depletion_mm", None)
                        profile = replace(profile, **overrides)
                        if initial_ponded is not None or initial_depletion is not None:
                            _, _, target = profile.stage_parameters(0)
                            initial_state = WaterState(float(initial_depletion or 0), float(target if initial_ponded is None else initial_ponded))
                            initial_state_source = "measured" if stored_profile.get("source") == "measured" else "user_profile"
                    irrigation = self.repository.irrigation_depths(command.field_id, cycle_start, end_date) if hasattr(self.repository, "irrigation_depths") else []
                    self.repository.set_status(request_id, "running_water_balance")
                    water_balance = calculate_paddy_balance(
                        historical, irrigation, profile, cycle_start,
                        initial_state=initial_state, initial_state_source=initial_state_source,
                        cycle_start_source=cycle_source, irrigation_history_complete=False,
                    )
                    water_chart = water_balance["daily"]
                    if hasattr(self.repository, "save_water_balance"):
                        self.repository.save_water_balance(request_id, water_balance)
                    if hasattr(self.repository, "save_result_payload"):
                        self.repository.save_result_payload(request_id, "water_balance", {key: value for key, value in water_balance.items() if key != "daily"})
                    modules["water_balance"] = _module_contract(water_balance)
                    self._save_module(request_id, "water_balance", modules["water_balance"])

                    projected_rows = []
                    if advisory_forecast and historical_lag_days == 0:
                        rain_credit = (0.8, 0.8, 0.6, 0.5, 0.4)
                        conservative_forecast = [
                            DailyWeather(item.date, item.rainfall_mm * rain_credit[min(index, 4)], item.et0_mm,
                                         item.kind, item.source, item.quality)
                            for index, item in enumerate(advisory_forecast)
                        ]
                        projection = calculate_paddy_balance(
                            conservative_forecast, [], profile, cycle_start,
                            initial_state=WaterState(**water_balance["final_state"]),
                            initial_state_source="calculated", cycle_start_source=cycle_source,
                            irrigation_history_complete=False,
                        )
                        projected_rows = projection["daily"]
                        for row in projected_rows:
                            row["rainfall_is_credited"] = True
                    self.repository.set_status(request_id, "running_irrigation_advisory")
                    if historical_lag_days:
                        irrigation_advisory = {
                            "status": "insufficient_data", "action": "unavailable",
                            "reason_code": "HISTORICAL_WEATHER_STALE", "provisional": True,
                            "evidence_level": "low", "rule_version": "paddy-advisory-v1",
                            "urgency": None, "reason": "The latest water-balance state is not current enough for irrigation advice.",
                            "net_depth_mm": None, "gross_depth_mm": None, "volume_m3": None,
                            "irrigation_efficiency": profile.irrigation_efficiency,
                            "forecast_rainfall_credited_mm": None, "trigger_crossing_date": None,
                            "warnings": [f"Historical weather is {historical_lag_days} day(s) behind; no current advisory was issued."],
                        }
                    else:
                        irrigation_advisory = build_irrigation_advisory(
                            water_balance, projected_rows, field_area_m2=geometry.area_m2,
                            irrigation_efficiency=profile.irrigation_efficiency,
                        )
                    if forecast_warning and irrigation_advisory.get("warnings") is not None:
                        irrigation_advisory["warnings"].append(forecast_warning)
                    if hasattr(self.repository, "save_advisory"):
                        self.repository.save_advisory(request_id, irrigation_advisory)
                    if hasattr(self.repository, "save_result_payload"):
                        self.repository.save_result_payload(request_id, "irrigation_advisory", irrigation_advisory)
                    modules["irrigation_advisory"] = _module_contract(irrigation_advisory)
                    self._save_module(request_id, "irrigation_advisory", modules["irrigation_advisory"])
                    warnings.extend(weather_result["warnings"] + water_balance["warnings"])
                    if irrigation_advisory["status"] != "completed":
                        status = "partial"
                except Exception as exc:
                    logger.exception("Weather or water-balance processing failed for analysis %s", request_id)
                    reason = exc.code if isinstance(exc, DomainError) else "WATER_BALANCE_FAILED"
                    message = exc.message if isinstance(exc, DomainError) else "Water-balance processing failed."
                    if "weather" not in modules:
                        modules["weather"] = {"status": "failed", "reason_code": reason, "provisional": True, "evidence_level": "low", "warnings": [message], "input_sources": []}
                    if "water_balance" not in modules:
                        modules["water_balance"] = {"status": "insufficient_data" if isinstance(exc, DomainError) else "failed", "reason_code": reason, "provisional": True, "evidence_level": "low", "warnings": [message], "input_sources": []}
                    modules["irrigation_advisory"] = {"status": "skipped", "reason_code": "WATER_BALANCE_UNAVAILABLE", "provisional": True, "evidence_level": "low", "warnings": [], "input_sources": []}
                    for module in ("weather", "water_balance", "irrigation_advisory"):
                        self._save_module(request_id, module, modules[module])
                    warnings.append(message)
                    status = "partial"
            modules = {name: _module_contract(result) for name, result in modules.items()}
            charts = build_charts(crop, stage, stress)
            charts["water_balance"] = water_chart
            if hasattr(self.repository, "save_result_payload"):
                self.repository.save_result_payload(request_id, "charts", charts)
            artifacts = []
            if command.generate_artifacts:
                try:
                    generated_artifacts, artifact_warnings = self.artifact_writer.write_analysis(request_id, crop, stage, probabilities, inputs, stress, water_balance, irrigation_advisory)
                    for artifact in generated_artifacts:
                        self.repository.save_artifact(request_id, artifact)
                        artifacts.append({**artifact, "download_url": f"/api/v1/analyses/{request_id}/artifacts/{artifact['type']}", "relative_path": None})
                    if artifact_warnings:
                        warnings.extend(artifact_warnings)
                        status = "partial"
                except DomainError as exc:
                    warnings.append(exc.message)
                    status = "partial"
                    logger.exception("Artifact generation failed for analysis %s", request_id)
                except Exception:
                    warnings.append("Artifacts could not be generated for this analysis.")
                    status = "partial"
                    logger.exception("Unexpected artifact generation failure for analysis %s", request_id)
            quality = {"crop_observations": [item.__dict__ for item in inputs.quality], "analysis_cutoff": today.isoformat() if command.year == today.year else f"{command.year}-12-31", "in_season": command.year == today.year and today < date(today.year, 11, 1)}
            self.repository.set_status(request_id, status, warnings=warnings, quality=quality)
            return {
                "request_id": str(request_id), "field_id": command.field_id, "status": status,
                "provider": {"name": inputs.provider, "live_data": inputs.live_data, "cached": inputs.cached},
                "geometry": {"revision_hash": geometry.geometry_hash, "area_m2": geometry.area_m2, "width_m": geometry.width_m, "height_m": geometry.height_m, "field_pixel_count": geometry.field_pixel_count},
                "data_quality": quality, "crop": crop, "growth_stage": stage,
                "moisture_stress": _strip_chart_data(stress) if stress else None,
                "modules": modules, "weather": weather_result, "water_balance": None if water_balance is None else {key: value for key, value in water_balance.items() if key != "daily"},
                "irrigation_advisory": irrigation_advisory,
                "charts": charts,
                "explanations": {
                    "confidence": "Mean model probability over field-mask pixels; it is not a measured accuracy.",
                    "stress_risk": "Evidence-based anomaly score from satellite signals. Provisional only — not a confirmed water-shortage diagnosis.",
                    "ndmi": "Normalised Difference Moisture Index — vegetation moisture-related signal.",
                    "ndvi": "Normalised Difference Vegetation Index — crop greenness and canopy condition.",
                    "radar": "Sentinel-1 SAR backscatter — field structure and surface moisture-related response.",
                },
                "artifacts": artifacts, "warnings": warnings,
                "provenance": {"model": self.crop_runtime.model_name, "checkpoint_sha256": self.crop_runtime.checkpoint_sha256, "preprocessing_version": PREPROCESSING_VERSION, "stage_rule_version": STAGE_RULE_VERSION, "stress_rule_version": STRESS_RULE_VERSION, "roi_version": self.settings.CAUVERY_ROI_VERSION},
            }
        except Exception as exc:
            code = exc.code if isinstance(exc, DomainError) else "CROP_INFERENCE_FAILED"
            message = exc.message if isinstance(exc, DomainError) else "Field analysis failed."
            self.repository.set_status(request_id, "failed", error_code=code, error_message=message)
            if isinstance(exc, DomainError):
                raise
            raise DomainError(code, message, 500) from exc

    def retrieve(self, request_id: UUID) -> dict | None:
        return self.repository.get_analysis(request_id)

    def history(self, field_id: str, limit: int, offset: int) -> list[dict]:
        return self.repository.history(field_id, limit, offset)
