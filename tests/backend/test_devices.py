"""Device endpoint tests — real HTTP, real SQLite, real contract validation."""
import copy


def test_create_device_returns_201(client, valid_device_payload):
    r = client.post("/devices", json=valid_device_payload)
    assert r.status_code == 201, r.text
    assert r.json()["device_id"] == valid_device_payload["device_id"]


def test_get_device_after_create(client, valid_device_payload):
    client.post("/devices", json=valid_device_payload)
    r = client.get(f"/devices/{valid_device_payload['device_id']}")
    assert r.status_code == 200
    assert r.json()["device_id"] == valid_device_payload["device_id"]


def test_get_unknown_device_returns_404(client):
    r = client.get("/devices/dev_does_not_exist")
    assert r.status_code == 404


def test_invalid_management_state_rejected(client, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    bad["management_state"] = "rooted"
    r = client.post("/devices", json=bad)
    assert r.status_code == 422


def test_battery_out_of_range_rejected(client, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    bad["battery"]["level_percent"] = 150
    r = client.post("/devices", json=bad)
    assert r.status_code == 422


def test_missing_required_field_rejected(client, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    del bad["device_id"]
    r = client.post("/devices", json=bad)
    assert r.status_code == 422


def test_injected_field_rejected(client, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    bad["injected_malicious"] = True
    r = client.post("/devices", json=bad)
    assert r.status_code == 422


def test_non_utc_timestamp_rejected(client, valid_device_payload):
    bad = copy.deepcopy(valid_device_payload)
    bad["last_seen"] = "2026-09-29 10:00:00"
    r = client.post("/devices", json=bad)
    assert r.status_code == 422


def test_list_devices_returns_created(client, valid_device_payload):
    client.post("/devices", json=valid_device_payload)
    r = client.get("/devices")
    assert r.status_code == 200
    assert len(r.json()["devices"]) == 1


def test_upsert_updates_existing(client, valid_device_payload):
    client.post("/devices", json=valid_device_payload)
    updated = copy.deepcopy(valid_device_payload)
    updated["battery"]["level_percent"] = 50
    updated["updated_at"] = "2026-09-29T11:00:00Z"
    r = client.post("/devices", json=updated)
    assert r.status_code == 201
    g = client.get(f"/devices/{valid_device_payload['device_id']}")
    assert g.json()["battery"]["level_percent"] == 50
    assert len(client.get("/devices").json()["devices"]) == 1
