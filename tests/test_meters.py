from datetime import datetime

from app.main import app
from app.models import ConsumptionReading, MeterDetail, MeterListResponse, MeterSummary
from fastapi.testclient import TestClient

client = TestClient(app)


def test_login_success(monkeypatch):
    from app import main as main_module

    monkeypatch.setattr(main_module.service, "login", lambda email=None, password=None: "ok")
    response = client.post("/api/v1/auth/login", json={"email": "operator@urja.local", "password": "secret"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_meters_success(monkeypatch):
    from app import main as main_module

    monkeypatch.setattr(
        main_module.service,
        "list_meters",
        lambda query="", page=1: MeterListResponse(
            items=[MeterSummary.model_validate({
                "meterId": "J100000",
                "serialNo": "SE33962",
                "make": "HPL",
                "phaseType": "single",
                "installStatus": "Installed",
                "dtCode": "DT-001",
            })],
            total=1,
            page=1,
            page_size=20,
        ),
    )

    response = client.get("/api/v1/meters", params={"q": "", "page": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["meter_id"] == "J100000"


def test_get_meter_success(monkeypatch):
    from app import main as main_module

    monkeypatch.setattr(
        main_module.service,
        "get_meter",
        lambda meter_id: MeterDetail(
            meter_id="J100000",
            serial_no="SE33962",
            make="HPL",
            phase_type="single",
            install_status="Installed",
            installation_type="Whole Current",
            latitude=26.93,
            longitude=75.83,
            hierarchy={"Zone": "Jaipur Zone 1 (Z-01)", "DT": "DT-001"},
            attributes={"Serial No": "SE33962"},
        ),
    )

    response = client.get("/api/v1/meters/J100000")
    assert response.status_code == 200
    assert response.json()["meter_id"] == "J100000"


def test_get_consumption_success(monkeypatch):
    from app import main as main_module

    monkeypatch.setattr(
        main_module.service,
        "get_consumption",
        lambda meter_id: [
            ConsumptionReading(
                timestamp=datetime(2026, 6, 23, 23, 30),
                kwh=48438.74,
                kvah=52313.84,
                volt_r=226.0,
            )
        ],
    )

    response = client.get("/api/v1/meters/J100000/consumption")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["kwh"] == 48438.74
