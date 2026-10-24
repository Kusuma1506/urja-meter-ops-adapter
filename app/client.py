from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import Settings
from app.exceptions import (
    ConfigurationError,
    MeterNotFoundError,
    UpstreamAuthenticationError,
    UpstreamBadResponseError,
    UpstreamError,
    UpstreamTimeoutError,
    ValidationError,
)
from app.models import ConsumptionReading, MeterDetail, MeterSummary


class UrjaPortalClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.URJA_BASE_URL.rstrip("/")
        self.username = settings.URJA_USERNAME
        self.password = settings.URJA_PASSWORD
        self.session = httpx.Client(
            base_url=self.base_url,
            follow_redirects=False,
            timeout=settings.REQUEST_TIMEOUT,
            headers={"User-Agent": "UrjaMeterOpsAdapter/1.0"},
        )
        self._authenticated = False

    def close(self) -> None:
        self.session.close()

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    def login(self, username: str | None = None, password: str | None = None) -> bool:
        username = username or self.username
        password = password or self.password
        if not username or not password:
            raise ConfigurationError("URJA_USERNAME and URJA_PASSWORD must be configured.")

        self.session.cookies.clear()
        self._authenticated = False
        headers = {
            "Origin": self.base_url,
            "Referer": urljoin(self.base_url, "/login"),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            response = self.session.post(
                "/login",
                data={"email": username, "password": password},
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(str(exc), status_code=503) from exc

        if response.status_code in (302, 303):
            location = (response.headers.get("location") or "").lower()
            if "/meters" in location or "/transformers" in location or location == "/":
                self._authenticated = True
                return True

        body_text = response.text.lower()
        if "cross-site post form submissions are forbidden" in body_text:
            raise UpstreamBadResponseError("The login form is enforcing a CSRF policy and the client headers do not satisfy it.")
        if "sign in" in body_text and "invalid" in body_text:
            raise UpstreamAuthenticationError("The provided upstream credentials were invalid.")
        if response.status_code == 401 or "invalid" in body_text:
            raise UpstreamAuthenticationError("The provided upstream credentials were invalid.")
        if response.status_code == 200 and "redirect" in body_text and "/meters" in body_text:
            self._authenticated = True
            return True
        if response.status_code == 200 and "ops desk" in body_text:
            self._authenticated = True
            return True

        raise UpstreamAuthenticationError("The upstream portal rejected the authentication attempt.")

    def _ensure_authenticated(self) -> None:
        if self._authenticated:
            return
        self.login()

    def _request_json(self, method: str, url: str, *, data: dict[str, Any] | None = None) -> Any:
        headers = {"Accept": "application/json, text/plain, */*"}
        try:
            response = self.session.request(method, url, data=data, headers=headers)
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(str(exc), status_code=503) from exc

        if response.status_code in (401, 403):
            raise UpstreamAuthenticationError("The upstream session has expired or is invalid.")
        if response.status_code in (301, 302, 303):
            location = response.headers.get("location", "")
            if "/login" in location.lower():
                raise UpstreamAuthenticationError("The upstream session expired and needs to be re-established.")
        if response.status_code >= 500:
            raise UpstreamError(f"Upstream portal returned HTTP {response.status_code}.", status_code=response.status_code)
        if response.status_code == 404:
            raise MeterNotFoundError(url.rsplit("/", 1)[-1])
        if response.status_code not in (200, 201):
            raise UpstreamBadResponseError(f"Unexpected upstream status {response.status_code} for URL {url}.")

        try:
            return response.json()
        except ValueError as exc:
            raise UpstreamBadResponseError("The legacy portal response was not valid JSON.") from exc

    def search_meters(self, query: str = "", page: int = 1) -> tuple[list[MeterSummary], int]:
        if page < 1:
            raise ValidationError("Page must be at least 1.")
        self._ensure_authenticated()
        payload = self._request_json("GET", f"/portal/meters/search?q={query}&page={page}")
        items = payload.get("data", [])
        total = int(payload.get("total", len(items)))
        return [MeterSummary.model_validate(item) for item in items], total

    def get_meter_detail(self, meter_id: str) -> MeterDetail:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", meter_id):
            raise ValidationError("Meter ID is malformed.")
        self._ensure_authenticated()
        page_url = f"/meters/{meter_id}"
        try:
            response = self.session.get(page_url)
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(str(exc), status_code=503) from exc

        if response.status_code == 404:
            raise MeterNotFoundError(meter_id)
        if response.status_code >= 500:
            raise UpstreamError(f"Upstream portal returned HTTP {response.status_code}.", status_code=response.status_code)
        if response.status_code not in (200, 201):
            raise UpstreamBadResponseError(f"Unexpected upstream status {response.status_code} for {page_url}.")

        geo_payload = self._request_json("GET", f"/portal/meters/{meter_id}/geo")
        geo_data = geo_payload.get("data") or {}
        detail_data = self._parse_detail_payload(response.text, meter_id)

        latitude = geo_data.get("latitude")
        longitude = geo_data.get("longitude")
        attributes = {item["parameterName"]: item["parameterValue"] for item in detail_data.get("data", [])}
        hierarchy = detail_data.get("hierarchy", {})
        item = MeterDetail(
            meter_id=meter_id,
            serial_no=attributes.get("Serial No"),
            make=attributes.get("Make"),
            phase_type=attributes.get("Phase Type"),
            install_status=attributes.get("Installation Status"),
            installation_type=attributes.get("Installation Type"),
            latitude=float(str(latitude)) if latitude not in (None, "") else None,
            longitude=float(str(longitude)) if longitude not in (None, "") else None,
            hierarchy={str(key): str(value) for key, value in hierarchy.items()},
            attributes={str(key): str(value) for key, value in attributes.items()},
        )
        return item

    def _parse_detail_payload(self, html: str, meter_id: str) -> dict[str, Any]:
        patterns = [
            r'meterId:"?([^"\}]*)"?,detail:\{data:(\[.*?\]),hierarchy:(\{.*?\})\}',
            r'meterId:"?([^"\}]*)"?,detail:\{data:\[(.*?)\],hierarchy:(\{.*?\})\}',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.S)
            if match:
                meter_id_value, data_raw, hierarchy_raw = match.groups()
                break
        else:
            raise UpstreamBadResponseError(f"Meter detail page for {meter_id} was missing the expected embedded data.")

        try:
            data_items = json.loads(data_raw)
        except json.JSONDecodeError as exc:
            raise UpstreamBadResponseError("Meter detail payload was malformed.") from exc
        try:
            hierarchy = json.loads(hierarchy_raw)
        except json.JSONDecodeError:
            hierarchy = {}
        if not isinstance(data_items, list):
            raise UpstreamBadResponseError("Meter detail payload was not a list of parameters.")
        return {"meterId": meter_id_value.strip(), "data": data_items, "hierarchy": hierarchy}

    def get_meter_consumption(self, meter_id: str) -> list[ConsumptionReading]:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", meter_id):
            raise ValidationError("Meter ID is malformed.")
        self._ensure_authenticated()
        payload = self._request_json("GET", f"/portal/meters/{meter_id}/energy")
        entries = payload.get("data", [])
        readings: list[ConsumptionReading] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw_timestamp = entry.get("timestamp") or ""
            if not raw_timestamp:
                continue
            try:
                parsed = datetime.strptime(raw_timestamp, "%d/%m/%Y %H:%M")
            except ValueError:
                continue
            readings.append(
                ConsumptionReading(
                    timestamp=parsed,
                    kwh=float(entry["kwh"]) if entry.get("kwh") not in (None, "") else None,
                    kvah=float(entry["kvah"]) if entry.get("kvah") not in (None, "") else None,
                    volt_r=float(entry["voltR"]) if entry.get("voltR") not in (None, "") else None,
                )
            )
        return readings

    def get_hierarchy(self) -> list[dict[str, Any]]:
        self._ensure_authenticated()
        payload = self._request_json("GET", "/portal/meters/search?q=&page=1")
        data = payload.get("data", [])
        if not data:
            return []
        return [{"meter_id": item.get("meterId"), "dt_code": item.get("dtCode")} for item in data]

    @staticmethod
    def parse_consumption_payload(payload: dict[str, Any]) -> list[ConsumptionReading]:
        entries = payload.get("data", [])
        readings: list[ConsumptionReading] = []
        for entry in entries:
            raw_ts = (entry or {}).get("timestamp")
            if not raw_ts:
                continue
            try:
                dt = datetime.strptime(raw_ts, "%d/%m/%Y %H:%M")
            except ValueError:
                continue
            readings.append(
                ConsumptionReading(
                    timestamp=dt,
                    kwh=float((entry or {}).get("kwh")) if (entry or {}).get("kwh") not in (None, "") else None,
                    kvah=float((entry or {}).get("kvah")) if (entry or {}).get("kvah") not in (None, "") else None,
                    volt_r=float((entry or {}).get("voltR")) if (entry or {}).get("voltR") not in (None, "") else None,
                )
            )
        return readings
