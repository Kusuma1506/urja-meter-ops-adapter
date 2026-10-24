from __future__ import annotations

from app.client import UrjaPortalClient
from app.config import Settings
from app.exceptions import MeterNotFoundError, UpstreamAuthenticationError, UpstreamBadResponseError
from app.models import ConsumptionReading, HealthStatus, MeterDetail, MeterListResponse


class UrjaService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.client = UrjaPortalClient(self.settings)

    def health_check(self) -> HealthStatus:
        return HealthStatus(
            status="ok",
            service="urja-meter-ops-adapter",
            upstream="configured" if self.settings.URJA_BASE_URL else "unconfigured",
            auth_configured=bool(self.settings.URJA_USERNAME and self.settings.URJA_PASSWORD),
        )

    def login(self, username: str | None = None, password: str | None = None) -> str:
        if username is not None:
            self.client.username = username
        if password is not None:
            self.client.password = password
        self.client.login(username=username, password=password)
        return "ok"

    def list_meters(self, query: str = "", page: int = 1) -> MeterListResponse:
        items, total = self.client.search_meters(query=query, page=page)
        return MeterListResponse(items=items, total=total, page=page, page_size=20)

    def get_meter(self, meter_id: str) -> MeterDetail:
        try:
            return self.client.get_meter_detail(meter_id)
        except (MeterNotFoundError, UpstreamBadResponseError, UpstreamAuthenticationError):
            raise

    def get_consumption(self, meter_id: str) -> list[ConsumptionReading]:
        return self.client.get_meter_consumption(meter_id)

    def get_hierarchy(self):
        return self.client.get_hierarchy()
