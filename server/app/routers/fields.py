from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from app.config import settings

from app.core.exceptions import DomainError
from app.schemas.field_analysis import FieldAnalysisRequest
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
        "provisional": row["provisional"], "stage": row["stage"], "evidence": row["evidence"],
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
        "provisional": row.get("provisional", True),
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
    stress_charts = repository.get_stress_chart(request_id) if stress is not None else {"optical": [], "radar": []}
    if stress is not None:
        stress["chart_data"] = stress_charts
    artifacts = [{**item, "download_url": f"/api/v1/analyses/{request_id}/artifacts/{item['artifact_type']}"} for item in repository.list_artifacts(request_id)]
    result = {
        "request_id": row["request_id"], "field_id": row["field_code"],
        "geometry_revision": row["revision_number"], "status": row["status"],
        "provider": {"name": row["provider"], "live_data": row["provider_live_data"], "cached": row["provider_cached"]},
        "geometry": {"geojson": row["geometry"], "hash": row["geometry_hash"], "area_m2": row["area_m2"], "width_m": row["width_m"], "height_m": row["height_m"]},
        "data_quality": row["quality_metadata"], "crop": crop, "growth_stage": stage,
        "moisture_stress": stress,
        "charts": {
            "stage_timeline": repository.get_stage_chart(request_id),
            "stress_optical": stress_charts.get("optical", []),
            "stress_radar": stress_charts.get("radar", []),
        },
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
