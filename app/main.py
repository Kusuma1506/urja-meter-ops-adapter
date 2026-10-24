from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.exceptions import (
    ConfigurationError,
    MeterNotFoundError,
    UpstreamAuthenticationError,
    UpstreamBadResponseError,
    UpstreamError,
    UpstreamTimeoutError,
    ValidationError,
)
from app.models import ConsumptionReading, HealthStatus, LoginResponse, MeterDetail, MeterListResponse
from app.services import UrjaService

settings = get_settings()
service = UrjaService(settings)


class LoginRequest(BaseModel):
    email: str | None = Field(default=None, description="Upstream email address. Falls back to the configured URJA_USERNAME value.")
    password: str | None = Field(default=None, description="Upstream password. Falls back to the configured URJA_PASSWORD value.")


app = FastAPI(
    title="Urja Meter Ops Adapter",
    version="1.0.0",
    description="REST API adapter for the legacy Urja Meter Ops portal.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    response_model_by_alias=False,
)


@app.exception_handler(ValidationError)
async def validation_error_handler(_, exc: ValidationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(MeterNotFoundError)
async def meter_not_found_handler(_, exc: MeterNotFoundError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": f"Meter {exc.meter_id} was not found."}},
    )


@app.exception_handler(UpstreamTimeoutError)
async def timeout_handler(_, exc: UpstreamTimeoutError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(UpstreamAuthenticationError)
async def auth_handler(_, exc: UpstreamAuthenticationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(UpstreamBadResponseError)
async def bad_response_handler(_, exc: UpstreamBadResponseError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(UpstreamError)
async def upstream_error_handler(_, exc: UpstreamError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(_, exc: ConfigurationError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "CONFIGURATION_ERROR", "message": str(exc)}},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "The request payload or query parameters are invalid."}},
    )


@app.get("/health", response_model=HealthStatus, tags=["status"])
async def health() -> HealthStatus:
    return service.health_check()


@app.post("/api/v1/auth/login", response_model=LoginResponse, tags=["auth"])
async def login(payload: LoginRequest) -> LoginResponse:
    service.login(payload.email, payload.password)
    return LoginResponse(status="ok", message="Upstream authentication succeeded.")


@app.get("/api/v1/meters", response_model=MeterListResponse, tags=["meters"])
async def list_meters(
    q: str = Query(default="", description="Search query applied against the upstream meter search endpoint."),
    page: int = Query(default=1, ge=1, description="1-based page number."),
) -> MeterListResponse:
    return service.list_meters(query=q, page=page)


@app.get("/api/v1/meters/{meter_id}", response_model=MeterDetail, tags=["meters"])
async def get_meter(meter_id: str) -> MeterDetail:
    if not meter_id or not __import__('re').fullmatch(r"[A-Za-z0-9_-]+", meter_id):
        raise ValidationError("Meter ID is malformed.")
    return service.get_meter(meter_id)


@app.get("/api/v1/meters/{meter_id}/consumption", response_model=list[ConsumptionReading], tags=["meters"])
async def get_consumption(meter_id: str) -> list[ConsumptionReading]:
    if not meter_id or not __import__('re').fullmatch(r"[A-Za-z0-9_-]+", meter_id):
        raise ValidationError("Meter ID is malformed.")
    return service.get_consumption(meter_id)


@app.get("/api/v1/hierarchy", tags=["meters"])
async def hierarchy() -> dict:
    return {"items": service.get_hierarchy()}


@app.get("/", include_in_schema=False)
async def landingpage():
    return {"message": "Use /docs or /openapi.json to view the API."}
