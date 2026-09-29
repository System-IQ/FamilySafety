"""Derived Records — provenance enforcement + contract compliance."""
import pytest


@pytest.fixture
def production_algorithm(client, auth_headers):
    """Register gps_cleaning@1.0.0 and promote it to production."""
    client.post("/algorithms", headers=auth_headers, json={
        "algorithm_id": "gps_cleaning",
        "version": "1.0.0",
        "name": "GPS Cleaning (jump filter)",
        "input_schema_ref": "location.schema.json",
        "output_schema_ref": "derived_record.schema.json",
    })
    client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        headers=auth_headers,
        json={"test_status": "passing"},
    )
    for target in ("testing", "canary", "production"):
        r = client.post(
            "/algorithms/gps_cleaning/1.0.0/promote",
            headers=auth_headers, json={"target": target},
        )
        assert r.status_code == 200, r.text
    return {"algorithm_id": "gps_cleaning", "algorithm_version": "1.0.0"}


@pytest.fixture
def derived_payload(production_algorithm):
    return {
        "device_id": "dev_derived_001",
        "record_type": "cleaned_location",
        "timestamp": "2026-09-29T10:00:00Z",
        "payload": {
            "latitude": 33.3152,
            "longitude": 44.3661,
            "accuracy_meters": 6.2,
        },
        "provenance": {
            "source_record_ids": ["rec_001", "rec_002", "rec_003"],
            "algorithm_id": production_algorithm["algorithm_id"],
            "algorithm_version": production_algorithm["algorithm_version"],
            "confidence": 0.87,
            "evidence": ["3 source points used", "jump distance > threshold removed"],
        },
        "quality_score": 91.0,
    }


def _create(client, headers, payload):
    r = client.post("/derived", json=payload, headers=headers)
    return r


# ============================================================
# AUTH
# ============================================================

def test_create_requires_auth(client, derived_payload):
    assert client.post("/derived", json=derived_payload).status_code == 401


def test_list_requires_auth(client):
    assert client.get("/derived").status_code == 401


def test_get_requires_auth(client):
    assert client.get("/derived/drec_x").status_code == 401


# ============================================================
# HAPPY PATH
# ============================================================

def test_create_with_full_provenance(client, auth_headers, derived_payload):
    r = _create(client, auth_headers, derived_payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["record_id"].startswith("drec_")
    assert body["provenance"]["algorithm_id"] == "gps_cleaning"
    assert body["provenance"]["algorithm_version"] == "1.0.0"
    assert body["provenance"]["confidence"] == 0.87
    assert body["provenance"]["evidence"] == [
        "3 source points used", "jump distance > threshold removed"
    ]
    assert body["quality_score"] == 91.0
    assert body["insufficient_data"] is False


def test_create_with_uncertainty(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["uncertainty"] = {
        "level": "medium",
        "notes": "Few GPS fixes; accuracy borderline",
    }
    r = _create(client, auth_headers, p)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["provenance"]["uncertainty"]["level"] == "medium"
    assert body["provenance"]["uncertainty"]["notes"].startswith("Few GPS")


def test_create_insufficient_data(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["insufficient_data"] = True
    p["insufficient_reason"] = "only 1 raw point available"
    r = _create(client, auth_headers, p)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["insufficient_data"] is True
    assert body["insufficient_reason"].startswith("only 1")


# ============================================================
# PROVENANCE ENFORCEMENT (Rule 2)
# ============================================================

def test_non_production_algorithm_rejected(client, auth_headers, derived_payload):
    # Register but do NOT promote
    client.post("/algorithms", headers=auth_headers, json={
        "algorithm_id": "stop_detection",
        "version": "0.5.0",
        "name": "Stop Detection",
        "input_schema_ref": "location.schema.json",
        "output_schema_ref": "derived_record.schema.json",
    })
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["algorithm_id"] = "stop_detection"
    p["provenance"]["algorithm_version"] = "0.5.0"
    r = _create(client, auth_headers, p)
    assert r.status_code == 409, r.text
    assert "production" in r.json()["detail"]


def test_wrong_version_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["algorithm_version"] = "9.9.9"
    r = _create(client, auth_headers, p)
    assert r.status_code == 409
    assert "production" in r.json()["detail"]


def test_unknown_algorithm_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["algorithm_id"] = "ghost_algo"
    r = _create(client, auth_headers, p)
    assert r.status_code == 409


# ============================================================
# VALIDATION RULES (1, 3, 4, 5, 6)
# ============================================================

def test_empty_source_record_ids_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["source_record_ids"] = []
    r = _create(client, auth_headers, p)
    assert r.status_code == 422


def test_confidence_above_one_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["confidence"] = 1.5
    r = _create(client, auth_headers, p)
    assert r.status_code == 422


def test_confidence_negative_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["confidence"] = -0.1
    r = _create(client, auth_headers, p)
    assert r.status_code == 422


def test_empty_evidence_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["evidence"] = []
    r = _create(client, auth_headers, p)
    assert r.status_code == 422


def test_quality_score_out_of_range_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["quality_score"] = 150.0
    r = _create(client, auth_headers, p)
    assert r.status_code == 422


def test_insufficient_data_without_reason_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["insufficient_data"] = True
    # no reason
    r = _create(client, auth_headers, p)
    assert r.status_code == 422


def test_invalid_record_type_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["record_type"] = "made_up_thing"
    r = _create(client, auth_headers, p)
    assert r.status_code == 422


def test_extra_field_rejected(client, auth_headers, derived_payload):
    p = dict(derived_payload)
    p["injected"] = True
    r = _create(client, auth_headers, p)
    assert r.status_code == 422


# ============================================================
# GET / LIST / FILTERS
# ============================================================

def test_get_by_id(client, auth_headers, derived_payload):
    r = _create(client, auth_headers, derived_payload)
    rid = r.json()["record_id"]
    r2 = client.get(f"/derived/{rid}", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["record_id"] == rid


def test_get_missing_404(client, auth_headers):
    r = client.get("/derived/drec_missing", headers=auth_headers)
    assert r.status_code == 404


def test_list_by_device(client, auth_headers, derived_payload):
    for dev in ("devA", "devA", "devB"):
        p = dict(derived_payload)
        p["device_id"] = dev
        _create(client, auth_headers, p)
    r = client.get("/derived", headers=auth_headers,
                   params={"device_id": "devA"})
    assert len(r.json()["records"]) == 2


def test_list_by_type(client, auth_headers, derived_payload):
    p2 = dict(derived_payload)
    p2["record_type"] = "route_summary"
    _create(client, auth_headers, derived_payload)
    _create(client, auth_headers, p2)
    r = client.get("/derived", headers=auth_headers,
                   params={"record_type": "cleaned_location"})
    assert len(r.json()["records"]) == 1


def test_list_by_min_quality(client, auth_headers, derived_payload):
    p1 = dict(derived_payload); p1["quality_score"] = 95.0
    p2 = dict(derived_payload); p2["quality_score"] = 40.0
    _create(client, auth_headers, p1)
    _create(client, auth_headers, p2)
    r = client.get("/derived", headers=auth_headers,
                   params={"min_quality": 80.0})
    assert len(r.json()["records"]) == 1


def test_list_excludes_insufficient(client, auth_headers, derived_payload):
    p1 = dict(derived_payload)
    p2 = dict(derived_payload)
    p2["insufficient_data"] = True
    p2["insufficient_reason"] = "test reason here"
    _create(client, auth_headers, p1)
    _create(client, auth_headers, p2)
    r = client.get("/derived", headers=auth_headers,
                   params={"include_insufficient": False})
    assert len(r.json()["records"]) == 1


# ============================================================
# AUDIT
# ============================================================

def test_audit_records_derived_create(client, auth_headers, derived_payload):
    r = _create(client, auth_headers, derived_payload)
    rid = r.json()["record_id"]
    aud = client.get("/audit", headers=auth_headers,
                     params={"action": "derived.create"})
    assert aud.status_code == 200
    records = aud.json()["audit"]
    assert len(records) == 1
    assert records[0]["resource_id"] == rid


# ============================================================
# CONTRACT COMPLIANCE
# ============================================================

def test_response_validates_against_contract(client, auth_headers, derived_payload):
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator, FormatChecker

    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (root / "shared" / "contracts" / "v2" / "derived_record.schema.json").read_text()
    )
    v = Draft202012Validator(schema, format_checker=FormatChecker())

    # standard
    r = _create(client, auth_headers, derived_payload)
    assert r.status_code == 201, r.text
    v.validate(r.json())

    # with uncertainty
    p = dict(derived_payload)
    p["provenance"] = dict(derived_payload["provenance"])
    p["provenance"]["uncertainty"] = {"level": "low", "notes": "minor"}
    v.validate(_create(client, auth_headers, p).json())

    # insufficient_data
    p2 = dict(derived_payload)
    p2["insufficient_data"] = True
    p2["insufficient_reason"] = "not enough points"
    v.validate(_create(client, auth_headers, p2).json())
