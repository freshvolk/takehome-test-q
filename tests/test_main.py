from fastapi.testclient import TestClient

from app.main import VERSION_ENV, app


def test_read_healthz():
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_read_version_unset(monkeypatch):
    monkeypatch.delenv(VERSION_ENV, raising=False)
    with TestClient(app) as client:
        response = client.get("/version")
        assert response.status_code == 200
        assert response.json() == {"version": "unset"}


def test_read_version_set(monkeypatch):
    test_ver = "1.33.1"
    monkeypatch.setenv(VERSION_ENV, test_ver)
    with TestClient(app) as client:
        response = client.get("/version")
        assert response.status_code == 200
        assert response.json() == {"version": test_ver}
