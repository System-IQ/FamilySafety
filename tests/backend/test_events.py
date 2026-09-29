"""Events endpoints — auth, validation, contract, filters."""
import pytest


@pytest.fixture
def valid_event_payload():
    return {
        "device_id": "dev_events_001",
        "event_type": "device_online",
        "severity": "info",
        "timestamp": "2026-09-29T10:00:00Z",
        "payload": {"ip": "10.0.0.5"},
    }


def test_post_event_without_auth_fails(client, valid_event_payload):
    r = client.post("/events", json=valid_event_payload)
    assert r.status_code == 401


def test_post_event_creates(client, auth_headers, valid_event_payload):
    r = client.post("/events", json=valid_event_payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["event_id"].startswith("evt_")
    assert body["device_id"] == valid_event_payload["device_id"]
    assert body["event_type"] == "device_online"
    assert body["payload"] == {"ip": "10.0.0.5"}


def test_post_event_invalid_type_fails(client, auth_headers, valid_event_payload):
    bad = dict(valid_event_payload)
    bad["event_type"] = "teleport"
    r = client.post("/events", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_post_event_invalid_severity_fails(client, auth_headers, valid_event_payload):
    bad = dict(valid_event_payload)
    bad["severity"] = "meh"
    r = client.post("/events", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_post_event_extra_field_rejected(client, auth_headers, valid_event_payload):
    bad = dict(valid_event_payload)
    bad["injected"] = True
    r = client.post("/events", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_get_event_by_id(client, auth_headers, valid_event_payload):
    r = client.post("/events", json=valid_event_payload, headers=auth_headers)
    eid = r.json()["event_id"]
    r = client.get(f"/events/{eid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["event_id"] == eid


def test_get_missing_event_404(client, auth_headers):
    r = client.get("/events/evt_missing_does_not_exist", headers=auth_headers)
    assert r.status_code == 404


def test_list_events_requires_auth(client):
    assert client.get("/events").status_code == 401


def test_list_events_returns_all(client, auth_headers, valid_event_payload):
    for i in range(3):
        p = dict(valid_event_payload)
        p["device_id"] = f"dev_{i}"
        client.post("/events", json=p, headers=auth_headers)
    r = client.get("/events", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["events"]) == 3


def test_filter_by_device(client, auth_headers, valid_event_payload):
    for dev in ("devA", "devA", "devB"):
        p = dict(valid_event_payload)
        p["device_id"] = dev
        client.post("/events", json=p, headers=auth_headers)
    r = client.get("/events", headers=auth_headers, params={"device_id": "devA"})
    assert r.status_code == 200
    assert len(r.json()["events"]) == 2


def test_filter_by_event_type(client, auth_headers, valid_event_payload):
    p1 = dict(valid_event_payload)
    p1["event_type"] = "device_online"
    p2 = dict(valid_event_payload)
    p2["event_type"] = "sos_triggered"
    p2["severity"] = "critical"
    client.post("/events", json=p1, headers=auth_headers)
    client.post("/events", json=p2, headers=auth_headers)
    r = client.get("/events", headers=auth_headers, params={"event_type": "sos_triggered"})
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1
    assert r.json()["events"][0]["severity"] == "critical"


def test_filter_by_since(client, auth_headers, valid_event_payload):
    early = dict(valid_event_payload)
    early["timestamp"] = "2026-09-29T09:00:00Z"
    late = dict(valid_event_payload)
    late["timestamp"] = "2026-09-29T11:00:00Z"
    client.post("/events", json=early, headers=auth_headers)
    client.post("/events", json=late, headers=auth_headers)
    r = client.get("/events", headers=auth_headers, params={"since": "2026-09-29T10:00:00Z"})
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1
    assert r.json()["events"][0]["timestamp"] == "2026-09-29T11:00:00Z"


def test_correlation_id_roundtrip(client, auth_headers, valid_event_payload):
    p = dict(valid_event_payload)
    p["correlation_id"] = "corr_abc_12345"
    r = client.post("/events", json=p, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["correlation_id"] == "corr_abc_12345"
