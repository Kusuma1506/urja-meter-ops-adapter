from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class MeterSummary(BaseModel):
    meter_id: str = Field(validation_alias="meterId")
    serial_no: str | None = Field(default=None, validation_alias="serialNo")
    make: str | None = None
    phase_type: str | None = Field(default=None, validation_alias="phaseType")
    install_status: str | None = Field(default=None, validation_alias="installStatus")
    dt_code: str | None = Field(default=None, validation_alias="dtCode")

    model_config = {"populate_by_name": True, "validate_by_name": True}


class MeterListResponse(BaseModel):
    items: list[MeterSummary]
    total: int
    page: int
    page_size: int = 20


class MeterDetail(BaseModel):
    meter_id: str
    serial_no: str | None = None
    make: str | None = None
    phase_type: str | None = None
    install_status: str | None = None
    installation_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    hierarchy: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, str] = Field(default_factory=dict)


class ConsumptionReading(BaseModel):
    timestamp: datetime
    kwh: float | None = None
    kvah: float | None = None
    volt_r: float | None = None


class HealthStatus(BaseModel):
    status: str
    service: str
    upstream: str
    auth_configured: bool


class LoginResponse(BaseModel):
    status: str = "ok"
    message: str = "Upstream authentication succeeded."


class HierarchyNode(BaseModel):
    name: str
    value: str | None = None
    children: list["HierarchyNode"] = Field(default_factory=list)


class HierarchyResponse(BaseModel):
    items: list[HierarchyNode]
    total: int
