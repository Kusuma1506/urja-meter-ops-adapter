from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "urja-meter-ops-adapter"


def test_root_redirect_info():
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()["message"]
