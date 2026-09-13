from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import DomainError
from app.core.lifespan import lifespan
from app.routers.fields import router as fields_router
from app.routers.health import router as health_router
from app.utils.response import error, success

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="Cauvery-only SICKLE field analysis API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_guard(request: Request, call_next):
    request.state.request_id = str(uuid4())
    content_length = request.headers.get("content-length")
    try:
        declared_too_large = bool(content_length and int(content_length) > 1_000_000)
    except ValueError:
        declared_too_large = True
    if declared_too_large:
        return JSONResponse(error("Request body is too large.", "INVALID_GEOMETRY", request.state.request_id), status_code=413)
    if request.method in {"POST", "PUT", "PATCH"} and len(await request.body()) > 1_000_000:
        return JSONResponse(error("Request body is too large.", "INVALID_GEOMETRY", request.state.request_id), status_code=413)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(error(exc.message, exc.code, getattr(request.state, "request_id", None)), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    is_field_analysis = request.url.path.endswith("/fields/analyze")
    code = "INVALID_GEOMETRY" if is_field_analysis else "INVALID_REQUEST"
    message = "Check the field boundary and analysis inputs." if is_field_analysis else "Check the submitted values and try again."
    return JSONResponse(error(message, code, getattr(request.state, "request_id", None)), status_code=422)


app.include_router(fields_router)
app.include_router(health_router)


@app.get("/")
def root():
    return success("AI Agriculture API Running")
