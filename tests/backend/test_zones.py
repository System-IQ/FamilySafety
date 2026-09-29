"""Safe Zones — CRUD, evaluate, events integration, audit."""
import pytest


@pytest.fixture
def zone_payload():
    return {
        "device_id": "dev_zone_001",
        "name": "Home",
        "center": {"latitude": 33.3152, "longitude": 44.3661},
        "radius_meters": 150.0,
        "enabled": True,
        "schedule": None,
    }


def _create_zone(client, headers, payload):
    r = client.post("/zones", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ============================================================
# AUTH
# ============================================================

def test_create_zone_requires_auth(client, zone_payload):
    assert client.post("/zones", json=zone_payload).status_code == 401


def test_list_zones_requires_auth(client):
    assert client.get("/zones").status_code == 401


def test_get_zone_requires_auth(client):
    assert client.get("/zones/zone_whatever").status_code == 401


def test_evaluate_requires_auth(client):
    r = client.post("/zones/zone_x/evaluate", json={
        "latitude": 0.0, "longitude": 0.0,
    })
    assert r.status_code == 401


# ============================================================
# CREATE
# ============================================================

def test_create_zone_minimal(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    assert z["zone_id"].startswith("zone_")
    assert z["device_id"] == zone_payload["device_id"]
    assert z["name"] == "Home"
    assert z["center"]["latitude"] == 33.3152
    assert z["radius_meters"] == 150.0
    assert z["enabled"] is True
    assert z["schedule"] is None


def test_create_zone_with_schedule(client, auth_headers, zone_payload):
    p = dict(zone_payload)
    p["schedule"] = {
        "days": ["mon", "tue", "wed"],
        "start_time": "07:00",
        "end_time": "14:00",
    }
    z = _create_zone(client, auth_headers, p)
    assert z["schedule"]["days"] == ["mon", "tue", "wed"]
    assert z["schedule"]["start_time"] == "07:00"


def test_create_zone_invalid_radius_fails(client, auth_headers, zone_payload):
    p = dict(zone_payload)
    p["radius_meters"] = 5   # < 10
    r = client.post("/zones", json=p, headers=auth_headers)
    assert r.status_code == 422


def test_create_zone_invalid_lat_fails(client, auth_headers, zone_payload):
    p = dict(zone_payload)
    p["center"] = {"latitude": 95.0, "longitude": 44.3661}
    r = client.post("/zones", json=p, headers=auth_headers)
    assert r.status_code == 422


def test_create_zone_invalid_day_fails(client, auth_headers, zone_payload):
    p = dict(zone_payload)
    p["schedule"] = {
        "days": ["funday"],
        "start_time": "07:00",
        "end_time": "14:00",
    }
    r = client.post("/zones", json=p, headers=auth_headers)
    assert r.status_code == 422


def test_create_zone_extra_field_rejected(client, auth_headers, zone_payload):
    p = dict(zone_payload)
    p["injected"] = True
    r = client.post("/zones", json=p, headers=auth_headers)
    assert r.status_code == 422


# ============================================================
# GET / LIST
# ============================================================

def test_get_zone_by_id(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    r = client.get(f"/zones/{z['zone_id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["zone_id"] == z["zone_id"]


def test_get_missing_zone_404(client, auth_headers):
    r = client.get("/zones/zone_missing", headers=auth_headers)
    assert r.status_code == 404


def test_list_zones_filter_by_device(client, auth_headers, zone_payload):
    for dev in ("devA", "devA", "devB"):
        p = dict(zone_payload)
        p["device_id"] = dev
        client.post("/zones", json=p, headers=auth_headers)
    r = client.get("/zones", headers=auth_headers, params={"device_id": "devA"})
    assert r.status_code == 200
    assert len(r.json()["zones"]) == 2


def test_list_zones_enabled_only(client, auth_headers, zone_payload):
    p1 = dict(zone_payload); p1["enabled"] = True
    p2 = dict(zone_payload); p2["enabled"] = False; p2["name"] = "Disabled"
    _create_zone(client, auth_headers, p1)
    _create_zone(client, auth_headers, p2)
    r = client.get("/zones", headers=auth_headers, params={"enabled_only": True})
    assert r.status_code == 200
    assert len(r.json()["zones"]) == 1


# ============================================================
# PATCH
# ============================================================

def test_patch_zone_updates_name_and_radius(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    r = client.patch(f"/zones/{z['zone_id']}", headers=auth_headers, json={
        "name": "Home Updated",
        "radius_meters": 250.0,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Home Updated"
    assert body["radius_meters"] == 250.0
    assert body["updated_at"] is not None


def test_patch_zone_clear_schedule(client, auth_headers, zone_payload):
    p = dict(zone_payload)
    p["schedule"] = {"days": ["mon"], "start_time": "07:00", "end_time": "14:00"}
    z = _create_zone(client, auth_headers, p)
    assert z["schedule"] is not None
    r = client.patch(f"/zones/{z['zone_id']}", headers=auth_headers, json={
        "clear_schedule": True,
    })
    assert r.status_code == 200
    assert r.json()["schedule"] is None


def test_patch_missing_zone_404(client, auth_headers):
    r = client.patch("/zones/zone_missing", headers=auth_headers, json={"name": "x"})
    assert r.status_code == 404


# ============================================================
# DELETE
# ============================================================

def test_delete_zone(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    r = client.delete(f"/zones/{z['zone_id']}", headers=auth_headers)
    assert r.status_code == 204
    assert client.get(f"/zones/{z['zone_id']}", headers=auth_headers).status_code == 404


def test_delete_missing_zone_404(client, auth_headers):
    r = client.delete("/zones/zone_missing", headers=auth_headers)
    assert r.status_code == 404


# ============================================================
# EVALUATE + events integration
# ============================================================

def test_evaluate_inside_emits_enter_event(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    r = client.post(f"/zones/{z['zone_id']}/evaluate",
                    headers=auth_headers,
                    json={
                        "latitude": 33.3152,
                        "longitude": 44.3661,
                        "at_utc": "2026-09-29T10:00:00Z",
                    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["inside"] is True
    assert body["entered"] is True
    assert body["exited"] is False
    assert body["event_id"] is not None

    ev = client.get(f"/events/{body['event_id']}", headers=auth_headers)
    assert ev.status_code == 200
    assert ev.json()["event_type"] == "safe_zone_enter"
    assert ev.json()["device_id"] == zone_payload["device_id"]


def test_evaluate_still_inside_no_event(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    client.post(f"/zones/{z['zone_id']}/evaluate",
                headers=auth_headers,
                json={"latitude": 33.3152, "longitude": 44.3661})
    r = client.post(f"/zones/{z['zone_id']}/evaluate",
                    headers=auth_headers,
                    json={"latitude": 33.3152, "longitude": 44.3661})
    assert r.status_code == 200
    body = r.json()
    assert body["inside"] is True
    assert body["entered"] is False
    assert body["exited"] is False
    assert body["event_id"] is None


def test_evaluate_exit_emits_exit_event(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    # first: enter
    client.post(f"/zones/{z['zone_id']}/evaluate",
                headers=auth_headers,
                json={"latitude": 33.3152, "longitude": 44.3661})
    # then: far away
    r = client.post(f"/zones/{z['zone_id']}/evaluate",
                    headers=auth_headers,
                    json={"latitude": 33.35, "longitude": 44.40})
    assert r.status_code == 200
    body = r.json()
    assert body["inside"] is False
    assert body["exited"] is True
    assert body["event_id"] is not None
    ev = client.get(f"/events/{body['event_id']}", headers=auth_headers)
    assert ev.json()["event_type"] == "safe_zone_exit"


def test_evaluate_disabled_zone_is_outside(client, auth_headers, zone_payload):
    p = dict(zone_payload)
    p["enabled"] = False
    z = _create_zone(client, auth_headers, p)
    r = client.post(f"/zones/{z['zone_id']}/evaluate",
                    headers=auth_headers,
                    json={"latitude": 33.3152, "longitude": 44.3661})
    assert r.status_code == 200
    assert r.json()["inside"] is False
    assert r.json()["enabled"] is False


def test_evaluate_missing_zone_404(client, auth_headers):
    r = client.post("/zones/zone_missing/evaluate", headers=auth_headers, json={
        "latitude": 0.0, "longitude": 0.0,
    })
    assert r.status_code == 404


def test_evaluate_respects_schedule(client, auth_headers, zone_payload):
    p = dict(zone_payload)
    p["schedule"] = {
        "days": ["mon"], "start_time": "07:00", "end_time": "14:00",
    }
    z = _create_zone(client, auth_headers, p)

    # Monday 10:00 UTC -> inside schedule
    mon = client.post(f"/zones/{z['zone_id']}/evaluate", headers=auth_headers, json={
        "latitude": 33.3152, "longitude": 44.3661,
        "at_utc": "2026-09-28T10:00:00Z",   # 2026-09-28 is Monday
    }).json()
    assert mon["within_schedule"] is True
    assert mon["inside"] is True

    # Sunday 10:00 UTC -> outside schedule
    sun = client.post(f"/zones/{z['zone_id']}/evaluate", headers=auth_headers, json={
        "latitude": 33.3152, "longitude": 44.3661,
        "at_utc": "2026-10-04T10:00:00Z",   # Sunday
    }).json()
    assert sun["within_schedule"] is False
    assert sun["inside"] is False


# ============================================================
# AUDIT
# ============================================================

def test_audit_records_zone_create(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "safe_zone.create"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1
    assert r.json()["audit"][0]["resource_id"] == z["zone_id"]


def test_audit_records_zone_update(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    client.patch(f"/zones/{z['zone_id']}", headers=auth_headers,
                 json={"name": "Updated"})
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "safe_zone.update"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1


def test_audit_records_zone_delete(client, auth_headers, zone_payload):
    z = _create_zone(client, auth_headers, zone_payload)
    client.delete(f"/zones/{z['zone_id']}", headers=auth_headers)
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "safe_zone.delete"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1
