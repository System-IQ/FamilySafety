"""Algorithms Registry — auth, CRUD, lifecycle, audit, schema compliance."""
import pytest


@pytest.fixture
def algo_payload():
    return {
        "algorithm_id": "gps_cleaning",
        "version": "1.0.0",
        "name": "GPS Cleaning (jump filter)",
        "description": "Removes GPS jumps based on speed thresholds",
        "input_schema_ref": "location.schema.json",
        "output_schema_ref": "derived_record.schema.json",
    }


def _register(client, headers, payload):
    r = client.post("/algorithms", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _promote(client, headers, aid, ver, target, **extra):
    body = {"target": target, **extra}
    return client.post(
        f"/algorithms/{aid}/{ver}/promote", json=body, headers=headers
    )


# ============================================================
# AUTH
# ============================================================

def test_register_requires_auth(client, algo_payload):
    assert client.post("/algorithms", json=algo_payload).status_code == 401


def test_list_requires_auth(client):
    assert client.get("/algorithms").status_code == 401


def test_get_requires_auth(client):
    assert client.get("/algorithms/x/1.0.0").status_code == 401


def test_promote_requires_auth(client, algo_payload):
    assert client.post("/algorithms/x/1.0.0/promote", json={"target": "testing"}).status_code == 401


# ============================================================
# REGISTER
# ============================================================

def test_register_creates_candidate(client, auth_headers, algo_payload):
    a = _register(client, auth_headers, algo_payload)
    assert a["algorithm_id"] == "gps_cleaning"
    assert a["version"] == "1.0.0"
    assert a["status"] == "candidate"
    assert a["test_status"] == "unknown"
    assert a["description"].startswith("Removes GPS")


def test_register_duplicate_fails_409(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    r = client.post("/algorithms", json=algo_payload, headers=auth_headers)
    assert r.status_code == 409


def test_register_invalid_id_rejected(client, auth_headers, algo_payload):
    bad = dict(algo_payload); bad["algorithm_id"] = "GPS-Clean!"
    r = client.post("/algorithms", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_register_invalid_version_rejected(client, auth_headers, algo_payload):
    bad = dict(algo_payload); bad["version"] = "1.0"
    r = client.post("/algorithms", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_register_extra_field_rejected(client, auth_headers, algo_payload):
    bad = dict(algo_payload); bad["injected"] = True
    r = client.post("/algorithms", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_register_multiple_versions(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    v2 = dict(algo_payload); v2["version"] = "1.1.0"
    _register(client, auth_headers, v2)
    r = client.get("/algorithms", headers=auth_headers,
                   params={"algorithm_id": "gps_cleaning"})
    assert len(r.json()["algorithms"]) == 2


# ============================================================
# GET / LIST
# ============================================================

def test_get_one(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    r = client.get("/algorithms/gps_cleaning/1.0.0", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["version"] == "1.0.0"


def test_get_missing_404(client, auth_headers):
    r = client.get("/algorithms/ghost/9.9.9", headers=auth_headers)
    assert r.status_code == 404


def test_list_filter_by_status(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    # Make it production
    client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "passing"}, headers=auth_headers,
    )
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "canary")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "production")

    # Add another candidate
    v2 = dict(algo_payload); v2["version"] = "1.1.0"
    _register(client, auth_headers, v2)

    r = client.get("/algorithms", headers=auth_headers,
                   params={"status": "production"})
    assert r.status_code == 200
    assert len(r.json()["algorithms"]) == 1
    assert r.json()["algorithms"][0]["version"] == "1.0.0"


# ============================================================
# TEST STATUS
# ============================================================

def test_set_test_status(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    r = client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "passing"}, headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["test_status"] == "passing"


def test_set_test_status_invalid(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    r = client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "amazing"}, headers=auth_headers,
    )
    assert r.status_code == 422


# ============================================================
# LIFECYCLE
# ============================================================

def test_promote_candidate_to_testing_requires_passing(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    r = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    assert r.status_code == 409
    assert "test_status=passing" in r.json()["detail"]


def test_full_promotion_chain(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "passing"}, headers=auth_headers,
    )

    r = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    assert r.status_code == 200 and r.json()["status"] == "testing"

    r = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "canary")
    assert r.status_code == 200 and r.json()["status"] == "canary"

    r = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "production")
    assert r.status_code == 200 and r.json()["status"] == "production"


def test_illegal_jump_candidate_to_production_409(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    r = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "production")
    assert r.status_code == 409
    assert "illegal transition" in r.json()["detail"]


def test_production_to_deprecated_with_reason(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "passing"}, headers=auth_headers,
    )
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "canary")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "production")

    r = _promote(
        client, auth_headers, "gps_cleaning", "1.0.0", "deprecated",
        reason="Replaced by 1.1.0", superseded_by="1.1.0",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "deprecated"
    assert body["deprecation_reason"] == "Replaced by 1.1.0"
    assert body["superseded_by"] == "1.1.0"
    assert body["deprecated_at"] is not None


def test_deprecated_is_terminal(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "passing"}, headers=auth_headers,
    )
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "canary")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "production")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "deprecated")

    r = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    assert r.status_code == 409


def test_block_candidate(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    r = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "blocked")
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"


def test_blocked_is_terminal(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "blocked")
    r = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    assert r.status_code == 409


def test_promote_missing_404(client, auth_headers):
    r = _promote(client, auth_headers, "ghost", "1.0.0", "testing")
    assert r.status_code == 404


# ============================================================
# GET PRODUCTION
# ============================================================

def test_get_production_version(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "passing"}, headers=auth_headers,
    )
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "canary")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "production")

    r = client.get("/algorithms/gps_cleaning/production", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["version"] == "1.0.0"


def test_get_production_missing_404(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    r = client.get("/algorithms/gps_cleaning/production", headers=auth_headers)
    assert r.status_code == 404


# ============================================================
# AUDIT
# ============================================================

def test_audit_records_register(client, auth_headers, algo_payload):
    a = _register(client, auth_headers, algo_payload)
    r = client.get("/audit", headers=auth_headers,
                   params={"action": "algorithm.register"})
    assert r.status_code == 200
    assert len(r.json()["audit"]) == 1
    assert r.json()["audit"][0]["resource_id"] == f"{a['algorithm_id']}@{a['version']}"


def test_audit_records_full_lifecycle(client, auth_headers, algo_payload):
    _register(client, auth_headers, algo_payload)
    client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "passing"}, headers=auth_headers,
    )
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "canary")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "production")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "deprecated")

    r = client.get("/audit", headers=auth_headers,
                   params={"resource_type": "algorithm"})
    actions = [a["action"] for a in r.json()["audit"]]
    assert actions.count("algorithm.register") == 1
    assert actions.count("algorithm.promote") >= 4
    assert actions.count("algorithm.deprecate") == 1


# ============================================================
# SCHEMA COMPLIANCE
# ============================================================

def test_response_validates_against_contract(client, auth_headers, algo_payload):
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator, FormatChecker

    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (root / "shared" / "contracts" / "v2" / "algorithm.schema.json").read_text()
    )
    v = Draft202012Validator(schema, format_checker=FormatChecker())

    a = _register(client, auth_headers, algo_payload)
    v.validate(a)

    client.patch(
        "/algorithms/gps_cleaning/1.0.0/test-status",
        json={"test_status": "passing"}, headers=auth_headers,
    )
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "testing")
    _promote(client, auth_headers, "gps_cleaning", "1.0.0", "canary")
    prod = _promote(client, auth_headers, "gps_cleaning", "1.0.0", "production").json()
    v.validate(prod)

    dep = _promote(
        client, auth_headers, "gps_cleaning", "1.0.0", "deprecated",
        reason="test", superseded_by="1.1.0",
    ).json()
    v.validate(dep)
