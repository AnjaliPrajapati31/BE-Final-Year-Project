from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.utils.response import success

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    return success("Service is healthy", {"status": "healthy"})


@router.get("/health/ready")
def readiness(request: Request):
    dependencies = request.app.state.dependencies
    ready = bool(dependencies) and all(
        item.get("ready", False) or item.get("required") is False
        for item in dependencies.values()
    ) and request.app.state.analysis_service is not None
    payload = {
        "success": ready,
        "message": "Service is ready" if ready else "Service is not ready",
        "data": {"status": "ready" if ready else "not_ready", "dependencies": dependencies},
    }
    return JSONResponse(payload, status_code=200 if ready else 503)
