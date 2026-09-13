from dataclasses import fields, replace
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from app.config import settings

from app.core.exceptions import DomainError
from app.schemas.field_analysis import FieldAnalysisRequest
from app.schemas.water import FieldWaterProfileUpdate, IrrigationEventCreate, IrrigationEventVoid
from app.services.water.balance import validate_profile
from app.services.water.profiles import CAUVERY_PADDY_V1
from app.utils.response import success

router = APIRouter(prefix="/api/v1", tags=["Field Analysis"])


def _service(request: Request):
    service = request.app.state.analysis_service
    if service is None:
        raise DomainError("MODEL_NOT_READY", "Production analysis dependencies are not ready.", 503)
    return service


def _repository(request: Request):
    repository = request.app.state.repository
    if repository is None:
        raise DomainError("DATABASE_NOT_READY", "Stored analyses are unavailable.", 503)
    return repository


@router.post("/fields/analyze")
def analyze_field(command: FieldAnalysisRequest, request: Request):
    result = _service(request).analyze(command)
    message = "Field analysis completed" if result["status"] == "completed" else "Field analysis completed with warnings"
    return success(message, result)


@router.get("/analyses/{request_id}")
def retrieve_analysis(request_id: UUID, request: Request):
    repository = _repository(request)
    row = repository.get_analysis(request_id)
    if row is None:
        raise DomainError("ANALYSIS_NOT_FOUND", "Analysis was not found.", 404)
    crop = None if row["class_code"] is None else {
        key: row[key] for key in (
            "class_code", "class_label", "confidence",
            "paddy_probability", "non_paddy_probability",
            "paddy_pixel_fraction", "non_paddy_pixel_fraction",
            "field_pixel_count", "s1_observation_count", "s2_observation_count",
            "used_months", "rejected_months", "experimental",
        )
    }
    stage = None if row["stage_status"] is None else {
        "status": row["stage_status"], "reason_code": row["reason_code"],
        "provisional": row["stage_provisional"], "stage": row["stage"], "evidence": row["evidence"],
        "cycle_start": row["cycle_start"], "latest_observation": row["latest_observation"],
        "current_cycle_count": row["current_cycle_count"],
        "current_cycle_span_days": row["current_cycle_span_days"],
        "latest_ndvi": row["latest_ndvi"], "latest_ndmi": row["latest_ndmi"],
        "peak_confirmed": row["peak_confirmed"],
        "maximum_interpretation": row["maximum_interpretation"],
        "selected_s1_orbit_pass": row["selected_s1_orbit_pass"],
        "selected_s1_orbit_number": row["selected_s1_orbit_number"],
        "clean_s1_observation_count": row["clean_s1_observation_count"],
        "clean_s2_observation_count": row["clean_s2_observation_count"],
        "warning": row["stage_warning"],
    }
    stress = None if row.get("stress_status") is None else {
        "status": row["stress_status"],
        "reason_code": row.get("stress_reason_code"),
        "provisional": row.get("stress_provisional", True),
        "stress_risk": row.get("stress_risk"),
        "stress_score": row.get("stress_score"),
        "latest_observation_date": row.get("stress_latest_obs"),
        "persistence_observations": row.get("persistence_observations"),
        "stage_context": row.get("stage_context"),
        "stage_evidence": row.get("stress_stage_evidence"),
        "evidence": row.get("stress_evidence") or [],
        "counter_evidence": row.get("stress_counter_evidence") or [],
        "warning": row.get("stress_warning"),
        "stress_rule_version": row.get("stress_rule_version"),
    }
    payloads = repository.get_result_payloads(request_id)
    crop = payloads.get("crop", crop)
    stage = payloads.get("growth_stage", stage)
    stress = payloads.get("moisture_stress", stress)
    artifacts = [{
        "type": item["artifact_type"], "relative_path": None, "mime_type": item["mime_type"],
        "size": item["size_bytes"], "sha256": item["sha256"],
        "download_url": f"/api/v1/analyses/{request_id}/artifacts/{item['artifact_type']}",
    } for item in repository.list_artifacts(request_id)]
    water = repository.get_water_results(request_id)
    modules = repository.get_module_runs(request_id)
    charts = payloads.get("charts")
    if charts is None:
        stress_charts = repository.get_stress_chart(request_id) if stress is not None else {"optical": [], "radar": []}
        charts = {
            "crop_probabilities": [] if crop is None else [
                {"label": "Paddy", "value": crop["paddy_probability"]},
                {"label": "Non-Paddy", "value": crop["non_paddy_probability"]},
            ],
            "stage_timeline": [] if stage is None else (
                stage["timeline"] if "timeline" in stage else repository.get_stage_chart(request_id)
            ),
            "stress_optical": stress_charts.get("optical", []),
            "stress_radar": stress_charts.get("radar", []),
            "water_balance": water["water_balance_daily"],
        }
    result = {
        "request_id": row["request_id"], "field_id": row["field_code"],
        "geometry_revision": row["revision_number"], "status": row["status"],
        "provider": {"name": row["provider"], "live_data": row["provider_live_data"], "cached": row["provider_cached"]},
        "geometry": {"geojson": row["geometry"], "hash": row["geometry_hash"], "area_m2": row["area_m2"], "width_m": row["width_m"], "height_m": row["height_m"]},
        "data_quality": row["quality_metadata"], "crop": crop, "growth_stage": stage,
        "moisture_stress": stress,
        "modules": modules, "weather": water["weather"],
        "water_balance": water["water_balance"],
        "irrigation_advisory": water["irrigation_advisory"],
        "charts": charts,
        "warnings": row["warnings"], "artifacts": artifacts,
        "provenance": {
            "model": row["model_name"], "checkpoint_sha256": row["checkpoint_sha256"],
            "preprocessing_version": row["preprocessing_version"],
            "stage_rule_version": row["stage_rule_version"],
            "stress_rule_version": row.get("stress_rule_version"),
            "roi_version": row["roi_version"],
        },
    }
    return success("Stored field analysis retrieved", result)



@router.get("/fields/{field_id}/analyses")
def field_history(request: Request, field_id: str, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    items = _repository(request).history(field_id, limit, offset)
    return success("Field analysis history retrieved", {"items": items, "limit": limit, "offset": offset})


@router.put("/fields/{field_id}/water-profile")
def update_water_profile(field_id: str, command: FieldWaterProfileUpdate, request: Request):
    values = command.model_dump(exclude={"profile_version", "source"}, exclude_none=True)
    existing = _repository(request).get_water_profile(field_id)
    combined = {**((existing or {}).get("overrides") or {}), **values}
    profile_keys = {item.name for item in fields(CAUVERY_PADDY_V1)} - {"version"}
    try:
        validate_profile(replace(CAUVERY_PADDY_V1, **{key: value for key, value in combined.items() if key in profile_keys}))
    except (TypeError, ValueError) as exc:
        raise DomainError("INVALID_WATER_PROFILE", str(exc), 422) from exc
    result = _repository(request).save_water_profile(field_id, command.profile_version, combined, command.source)
    return success("Field water profile stored", result)


@router.get("/fields/{field_id}/water-profile")
def retrieve_water_profile(field_id: str, request: Request):
    result = _repository(request).get_water_profile(field_id)
    return success("Field water profile retrieved", result or {"profile_version": "cauvery-paddy-v1", "source": "default", "overrides": {}})


@router.post("/fields/{field_id}/irrigation-events", status_code=201)
def create_irrigation_event(field_id: str, command: IrrigationEventCreate, request: Request):
    result = _repository(request).create_irrigation_event(field_id, command.model_dump())
    return success("Irrigation event stored", result)


@router.get("/fields/{field_id}/irrigation-events")
def list_irrigation_events(field_id: str, request: Request):
    return success("Irrigation event history retrieved", _repository(request).list_irrigation_events(field_id))


@router.post("/fields/{field_id}/irrigation-events/{event_id}/void")
def void_irrigation_event(field_id: str, event_id: UUID, command: IrrigationEventVoid, request: Request):
    result = _repository(request).void_irrigation_event(field_id, event_id, command.reason)
    return success("Irrigation event voided", result)


@router.get("/analyses/{request_id}/artifacts/{artifact_type}")
def download_artifact(request_id: UUID, artifact_type: str, request: Request):
    record = _repository(request).get_artifact(request_id, artifact_type)
    if record is None:
        raise DomainError("ARTIFACT_NOT_FOUND", "Artifact was not found.", 404)
    root = settings.path(settings.SICKLE_ARTIFACT_ROOT).resolve()
    path = (root / record["relative_path"]).resolve()
    if root not in path.parents or not path.is_file():
        raise DomainError("ARTIFACT_NOT_FOUND", "Artifact was not found.", 404)
    return FileResponse(path, media_type=record["mime_type"], filename=path.name)
