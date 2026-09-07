from fastapi.testclient import TestClient

from app import main


def test_health_remains_public_when_api_key_is_enabled(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "secret-key")
    client = TestClient(main.app)
    response = client.get("/api/health")
    assert response.status_code == 200


def test_api_requires_key_when_configured(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "secret-key")
    client = TestClient(main.app)
    response = client.get("/api/schema/fields")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_api_accepts_exact_configured_key(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "secret-key")
    client = TestClient(main.app)
    response = client.get("/api/schema/fields", headers={"X-API-Key": "secret-key"})
    assert response.status_code == 200
    assert "fields" in response.json()


def test_wrong_api_key_is_rejected(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "secret-key")
    client = TestClient(main.app)
    response = client.get("/api/schema/fields", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401
