"""Device endpoint tests — auth required after A2 policy change."""
import copy


def test_create_device_without_auth_fails(client, valid_device_payload):
    r = client.post("/devices", json=valid_device_payload)
    assert r.status_code == 401


def test_create_device_returns_201(client, auth_headers, valid_device_payload):
    r = client.post("/devices", json=valid_device_payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    assert r.json()["device_id"] == valid_device_payload["device_id"]


def test_get_device_after_create(client, auth_headers, valid_device_payload):
    client.post("/devices", json=valid_device_payload, headers=auth_headers)
    r = client.get(f"/devices/{valid_device_payload['device_id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["device_id"] == valid_device_payload["device_id"]


def test_get_unknown_device_returns_404(client, auth_headers):
    r = client.get("/devices/dev_does_not_exist", headers=auth_headers)
    assert r.status_code == 404


def test_get_devices_requires_auth(client):
    assert client.get("/devices").status_code == 401


def test_invalid_management_state_rejected(client, auth_headers, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    bad["management_state"] = "rooted"
    r = client.post("/devices", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_battery_out_of_range_rejected(client, auth_headers, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    bad["battery"]["level_percent"] = 150
    r = client.post("/devices", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_missing_required_field_rejected(client, auth_headers, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    del bad["device_id"]
    r = client.post("/devices", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_injected_field_rejected(client, auth_headers, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    bad["injected_malicious"] = True
    r = client.post("/devices", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_non_utc_timestamp_rejected(client, auth_headers, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    bad["last_seen"] = "2026-09-29 10:00:00"
    r = client.post("/devices", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_list_devices_returns_created(client, auth_headers, valid_device_payload):
    client.post("/devices", json=valid_device_payload, headers=auth_headers)
    r = client.get("/devices", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["devices"]) == 1


def test_upsert_updates_existing(client, auth_headers, valid_device_payload):
    client.post("/devices", json=valid_device_payload, headers=auth_headers)
    updated = copy.deepcopy(valid_device_payload)
    updated["battery"]["level_percent"] = 50
    updated["updated_at"] = "2026-09-29T11:00:00Z"
    r = client.post("/devices", json=updated, headers=auth_headers)
    assert r.status_code == 201
    g = client.get(f"/devices/{valid_device_payload['device_id']}", headers=auth_headers)
    assert g.json()["battery"]["level_percent"] == 50
    assert len(client.get("/devices", headers=auth_headers).json()["devices"]) == 1


def test_audit_records_device_create(client, auth_headers, valid_device_payload):
    client.post("/devices", json=valid_device_payload, headers=auth_headers)
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "device.create"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1
    assert r.json()["audit"][0]["resource_id"] == valid_device_payload["device_id"]
