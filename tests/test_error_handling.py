from app.exceptions import MeterNotFoundError, UpstreamAuthenticationError, UpstreamTimeoutError
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_invalid_credentials_return_401(monkeypatch):
    from app import main as main_module

    def fail(email=None, password=None):
        raise UpstreamAuthenticationError("The provided upstream credentials were invalid.")

    monkeypatch.setattr(main_module.service, "login", fail)
    response = client.post("/api/v1/auth/login", json={"email": "bad", "password": "bad"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UPSTREAM_AUTH_FAILED"


def test_missing_meter_returns_404(monkeypatch):
    from app import main as main_module

    def fail(meter_id):
        raise MeterNotFoundError(meter_id)

    monkeypatch.setattr(main_module.service, "get_meter", fail)
    response = client.get("/api/v1/meters/J999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "METER_NOT_FOUND"


def test_upstream_timeout_returns_504(monkeypatch):
    from app import main as main_module

    def fail(query="", page=1):
        raise UpstreamTimeoutError()

    monkeypatch.setattr(main_module.service, "list_meters", fail)
    response = client.get("/api/v1/meters", params={"q": "", "page": 1})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


def test_malformed_meter_id_returns_400(monkeypatch):
    from app import main as main_module

    def fail(meter_id):
        raise ValueError("bad")

    monkeypatch.setattr(main_module.service, "get_meter", fail)
    response = client.get("/api/v1/meters/not-valid!!")
    assert response.status_code == 400
