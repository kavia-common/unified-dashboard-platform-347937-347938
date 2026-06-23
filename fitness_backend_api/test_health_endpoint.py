from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok_true() -> None:
    """Smoke test: ensure the health endpoint responds and returns ok=true."""
    client = TestClient(app)

    resp = client.get("/api/health")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload == {"ok": True}
