from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from app.core.exceptions import DomainError

from .charts import build_charts
from .crop import PREPROCESSING_VERSION, summarize_crop, validate_crop_inputs
from .geometry import validate_geometry
from .stage import STAGE_RULE_VERSION, estimate_stage, skipped_non_paddy, unavailable


class AnalysisService:
    def __init__(self, settings, roi, repository, provider, crop_runtime, artifact_writer):
        self.settings = settings
        self.roi = roi
        self.repository = repository
        self.provider = provider
        self.crop_runtime = crop_runtime
        self.artifact_writer = artifact_writer

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
            warnings = [f"Missing usable {sensor} months: {', '.join(months)}" for sensor, months in crop["rejected_months"].items() if months]
            today = date.today()
            if command.year == today.year and today < date(today.year, 11, 1):
                warnings.insert(0, f"In-season experimental result using observations available through {today.isoformat()}; future observations were not fabricated.")
            if crop["class_label"] != "Paddy":
                stage = skipped_non_paddy()
                self.repository.save_stage(request_id, stage)
                status = "completed"
            else:
                self.repository.set_status(request_id, "fetching_stage_data")
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
                if stage["status"] != "completed" or stage.get("reason_code") == "LOW_STAGE_EVIDENCE":
                    warnings.append(stage.get("warning") or "Growth stage is not available.")
                    status = "partial"
                else:
                    status = "completed"
            charts = build_charts(crop, stage)
            artifacts = []
            if command.generate_artifacts:
                for artifact in self.artifact_writer.write_analysis(request_id, crop, stage, probabilities, inputs):
                    self.repository.save_artifact(request_id, artifact)
                    artifacts.append({**artifact, "download_url": f"/api/v1/analyses/{request_id}/artifacts/{artifact['type']}", "relative_path": None})
            quality = {"crop_observations": [item.__dict__ for item in inputs.quality], "analysis_cutoff": today.isoformat() if command.year == today.year else f"{command.year}-12-31", "in_season": command.year == today.year and today < date(today.year, 11, 1)}
            self.repository.set_status(request_id, status, warnings=warnings, quality=quality)
            return {
                "request_id": str(request_id), "field_id": command.field_id, "status": status,
                "provider": {"name": inputs.provider, "live_data": inputs.live_data, "cached": inputs.cached},
                "geometry": {"revision_hash": geometry.geometry_hash, "area_m2": geometry.area_m2, "width_m": geometry.width_m, "height_m": geometry.height_m, "field_pixel_count": geometry.field_pixel_count},
                "data_quality": quality, "crop": crop, "growth_stage": stage, "charts": charts,
                "explanations": {"confidence": "Mean model probability over field-mask pixels; it is not a measured accuracy."},
                "artifacts": artifacts, "warnings": warnings,
                "provenance": {"model": self.crop_runtime.model_name, "checkpoint_sha256": self.crop_runtime.checkpoint_sha256, "preprocessing_version": PREPROCESSING_VERSION, "stage_rule_version": STAGE_RULE_VERSION, "roi_version": self.settings.CAUVERY_ROI_VERSION},
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
