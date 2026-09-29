"""Audit trail — every sensitive action is recorded automatically."""
import pytest


def test_audit_requires_auth(client):
    assert client.get("/audit").status_code == 401


def test_audit_records_register(client, registered_user, auth_headers):
    r = client.get("/audit", headers=auth_headers, params={"action": "user.register"})
    assert r.status_code == 200
    recs = r.json()["audit"]
    assert len(recs) == 1
    assert recs[0]["result"] == "success"
    assert recs[0]["actor_user_id"] == registered_user["user"]["user_id"]


def test_audit_records_login(client, registered_user, auth_headers):
    r = client.get("/audit", headers=auth_headers, params={"action": "user.login"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1


def test_audit_records_failed_login(client, registered_user, auth_headers):
    client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": "wrong-password-here",
    })
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "user.login_failed"})
    assert r.status_code == 200
    recs = r.json()["audit"]
    assert len(recs) == 1
    assert recs[0]["result"] == "failure"


def test_audit_records_duplicate_register(client, registered_user, auth_headers):
    client.post("/auth/register", json={
        "email": registered_user["email"],
        "password": "another-long-password-1",
        "display_name": "Dup",
    })
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "user.register"})
    # one success + one failure
    results = sorted(x["result"] for x in r.json()["audit"])
    assert results == ["failure", "success"]


def test_audit_records_refresh(client, auth_tokens, auth_headers):
    client.post("/auth/refresh", json={"refresh_token": auth_tokens["refresh_token"]})
    r = client.get("/audit", headers=auth_headers, params={"action": "user.refresh"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1


def test_audit_records_refresh_replay_as_failure(client, auth_tokens, auth_headers):
    old = auth_tokens["refresh_token"]
    assert client.post("/auth/refresh", json={"refresh_token": old}).status_code == 200
    # Replay
    assert client.post("/auth/refresh", json={"refresh_token": old}).status_code == 401

    r = client.get("/audit", headers=auth_headers,
                   params={"action": "user.refresh_failed"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1
    assert r.json()["audit"][0]["result"] == "failure"


def test_audit_records_device_create(client, auth_headers, valid_device_payload):
    client.post("/devices", json=valid_device_payload, headers=auth_headers)
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "device.create"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1
    assert r.json()["audit"][0]["resource_id"] == valid_device_payload["device_id"]


def test_audit_records_device_update(client, auth_headers, valid_device_payload):
    client.post("/devices", json=valid_device_payload, headers=auth_headers)
    updated = dict(valid_device_payload)
    updated["updated_at"] = "2026-09-29T11:00:00Z"
    client.post("/devices", json=updated, headers=auth_headers)
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "device.update"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1


def test_audit_filter_by_resource(client, auth_headers, valid_device_payload):
    client.post("/devices", json=valid_device_payload, headers=auth_headers)
    r = client.get("/audit", headers=auth_headers, params={
        "resource_type": "device",
        "resource_id": valid_device_payload["device_id"],
    })
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1


def test_audit_get_by_id(client, auth_headers, registered_user):
    r = client.get("/audit", headers=auth_headers, params={"action": "user.register"})
    aid = r.json()["audit"][0]["audit_id"]
    r2 = client.get(f"/audit/{aid}", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["audit_id"] == aid


def test_audit_missing_404(client, auth_headers):
    assert client.get("/audit/aud_missing_does_not_exist", headers=auth_headers).status_code == 404
