"""Health endpoint tests — real HTTP, real DB check."""


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["checks"]["database"]["ok"] is True
    assert body["checks"]["database"]["error"] is None
    assert body["uptime_seconds"] >= 0
