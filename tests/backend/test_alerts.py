"""Alerts — auth, CRUD, state machine, audit, schema compliance."""
import pytest


@pytest.fixture
def alert_payload():
    return {
        "device_id": "dev_alert_001",
        "alert_type": "sos",
        "severity": "critical",
        "note": "Child pressed SOS",
        "last_location": {
            "latitude": 33.3152,
            "longitude": 44.3661,
            "accuracy_meters": 8.0,
            "timestamp": "2026-09-29T10:00:00Z",
        },
        "battery_level_percent": 42,
    }


def _create(client, headers, payload):
    r = client.post("/alerts", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ============================================================
# AUTH
# ============================================================

def test_create_requires_auth(client, alert_payload):
    assert client.post("/alerts", json=alert_payload).status_code == 401


def test_list_requires_auth(client):
    assert client.get("/alerts").status_code == 401


def test_get_requires_auth(client):
    assert client.get("/alerts/alr_x").status_code == 401


def test_acknowledge_requires_auth(client):
    assert client.post("/alerts/alr_x/acknowledge", json={}).status_code == 401


def test_resolve_requires_auth(client):
    assert client.post("/alerts/alr_x/resolve", json={}).status_code == 401


def test_dismiss_requires_auth(client):
    assert client.post("/alerts/alr_x/dismiss", json={}).status_code == 401


# ============================================================
# CREATE
# ============================================================

def test_create_minimal(client, auth_headers):
    r = client.post("/alerts", headers=auth_headers, json={
        "device_id": "dev_alert_002",
        "alert_type": "low_battery",
        "severity": "warning",
    })
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["alert_id"].startswith("alr_")
    assert a["state"] == "new"
    assert a["alert_type"] == "low_battery"
    assert a["note"] is None
    assert a["last_location"] is None


def test_create_full(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    assert a["severity"] == "critical"
    assert a["note"] == "Child pressed SOS"
    assert a["battery_level_percent"] == 42
    assert a["last_location"]["latitude"] == 33.3152
    assert a["last_location"]["accuracy_meters"] == 8.0
    assert a["acknowledged_at"] is None
    assert a["resolved_at"] is None


def test_create_invalid_type_fails(client, auth_headers, alert_payload):
    bad = dict(alert_payload)
    bad["alert_type"] = "teleport"
    r = client.post("/alerts", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_create_invalid_severity_fails(client, auth_headers, alert_payload):
    bad = dict(alert_payload)
    bad["severity"] = "meh"
    r = client.post("/alerts", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_create_battery_out_of_range_fails(client, auth_headers, alert_payload):
    bad = dict(alert_payload)
    bad["battery_level_percent"] = 150
    r = client.post("/alerts", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_create_extra_field_rejected(client, auth_headers, alert_payload):
    bad = dict(alert_payload)
    bad["injected"] = True
    r = client.post("/alerts", json=bad, headers=auth_headers)
    assert r.status_code == 422


# ============================================================
# READ + FILTERS
# ============================================================

def test_get_by_id(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    r = client.get(f"/alerts/{a['alert_id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["alert_id"] == a["alert_id"]


def test_get_missing_404(client, auth_headers):
    r = client.get("/alerts/alr_missing", headers=auth_headers)
    assert r.status_code == 404


def test_list_by_device(client, auth_headers, alert_payload):
    for dev in ("devA", "devA", "devB"):
        p = dict(alert_payload)
        p["device_id"] = dev
        client.post("/alerts", json=p, headers=auth_headers)
    r = client.get("/alerts", headers=auth_headers, params={"device_id": "devA"})
    assert r.status_code == 200
    assert len(r.json()["alerts"]) == 2


def test_list_by_state(client, auth_headers, alert_payload):
    a1 = _create(client, auth_headers, alert_payload)
    _create(client, auth_headers, alert_payload)
    client.post(f"/alerts/{a1['alert_id']}/acknowledge",
                headers=auth_headers, json={})
    r = client.get("/alerts", headers=auth_headers, params={"state": "acknowledged"})
    assert len(r.json()["alerts"]) == 1
    r = client.get("/alerts", headers=auth_headers, params={"state": "new"})
    assert len(r.json()["alerts"]) == 1


def test_list_by_type(client, auth_headers, alert_payload):
    p2 = dict(alert_payload)
    p2["alert_type"] = "low_battery"
    p2["severity"] = "warning"
    _create(client, auth_headers, alert_payload)
    _create(client, auth_headers, p2)
    r = client.get("/alerts", headers=auth_headers, params={"alert_type": "sos"})
    assert len(r.json()["alerts"]) == 1


def test_list_by_severity(client, auth_headers, alert_payload):
    p2 = dict(alert_payload)
    p2["severity"] = "info"
    _create(client, auth_headers, alert_payload)
    _create(client, auth_headers, p2)
    r = client.get("/alerts", headers=auth_headers, params={"severity": "critical"})
    assert len(r.json()["alerts"]) == 1


# ============================================================
# STATE MACHINE
# ============================================================

def test_acknowledge_new(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    r = client.post(f"/alerts/{a['alert_id']}/acknowledge",
                    headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["state"] == "acknowledged"
    assert body["acknowledged_by"] is not None
    assert body["acknowledged_at"] is not None


def test_resolve_from_acknowledged(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    client.post(f"/alerts/{a['alert_id']}/acknowledge",
                headers=auth_headers, json={})
    r = client.post(f"/alerts/{a['alert_id']}/resolve",
                    headers=auth_headers, json={})
    assert r.status_code == 200
    assert r.json()["state"] == "resolved"
    assert r.json()["resolved_at"] is not None


def test_resolve_direct_from_new(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    r = client.post(f"/alerts/{a['alert_id']}/resolve",
                    headers=auth_headers, json={})
    assert r.status_code == 200
    assert r.json()["state"] == "resolved"


def test_dismiss_new_with_reason(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    r = client.post(f"/alerts/{a['alert_id']}/dismiss",
                    headers=auth_headers, json={"reason": "false positive"})
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "dismissed"
    assert body["dismiss_reason"] == "false positive"
    assert body["dismissed_at"] is not None


def test_acknowledge_after_resolved_409(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    client.post(f"/alerts/{a['alert_id']}/resolve", headers=auth_headers, json={})
    r = client.post(f"/alerts/{a['alert_id']}/acknowledge",
                    headers=auth_headers, json={})
    assert r.status_code == 409
    assert "illegal transition" in r.json()["detail"]


def test_resolve_after_dismissed_409(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    client.post(f"/alerts/{a['alert_id']}/dismiss",
                headers=auth_headers, json={})
    r = client.post(f"/alerts/{a['alert_id']}/resolve",
                    headers=auth_headers, json={})
    assert r.status_code == 409


def test_acknowledge_missing_404(client, auth_headers):
    r = client.post("/alerts/alr_missing/acknowledge", headers=auth_headers, json={})
    assert r.status_code == 404


# ============================================================
# AUDIT INTEGRATION
# ============================================================

def test_audit_records_create(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    r = client.get("/audit", headers=auth_headers, params={"action": "alert.create"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1
    assert r.json()["audit"][0]["resource_id"] == a["alert_id"]


def test_audit_records_full_lifecycle(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    client.post(f"/alerts/{a['alert_id']}/acknowledge", headers=auth_headers, json={})
    client.post(f"/alerts/{a['alert_id']}/resolve", headers=auth_headers, json={})
    r = client.get("/audit", headers=auth_headers, params={"resource_type": "alert"})
    actions = sorted(a["action"] for a in r.json()["audit"])
    assert actions == ["alert.acknowledge", "alert.create", "alert.resolve"]


def test_audit_records_dismiss(client, auth_headers, alert_payload):
    a = _create(client, auth_headers, alert_payload)
    client.post(f"/alerts/{a['alert_id']}/dismiss",
                headers=auth_headers, json={"reason": "test"})
    r = client.get("/audit", headers=auth_headers, params={"action": "alert.dismiss"})
    assert len(r.json()["audit"]) == 1


# ============================================================
# SCHEMA COMPLIANCE (via API response round-trip)
# ============================================================

def test_response_validates_against_contract(client, auth_headers, alert_payload):
    """Every response we emit must satisfy alert.schema.json."""
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator, FormatChecker

    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (root / "shared" / "contracts" / "v2" / "alert.schema.json").read_text()
    )
    v = Draft202012Validator(schema, format_checker=FormatChecker())

    a = _create(client, auth_headers, alert_payload)
    v.validate(a)

    a2 = client.post(f"/alerts/{a['alert_id']}/acknowledge",
                     headers=auth_headers, json={}).json()
    v.validate(a2)

    a3 = client.post(f"/alerts/{a['alert_id']}/resolve",
                     headers=auth_headers, json={}).json()
    v.validate(a3)

    b = _create(client, auth_headers, alert_payload)
    b2 = client.post(f"/alerts/{b['alert_id']}/dismiss",
                     headers=auth_headers, json={"reason": "spam"}).json()
    v.validate(b2)
