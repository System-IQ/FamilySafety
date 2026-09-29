"""Shared fixtures for contract tests (v1 + v2)."""
from pathlib import Path
import json
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
V1_DIR = REPO_ROOT / "shared" / "contracts" / "v1"
V2_DIR = REPO_ROOT / "shared" / "contracts" / "v2"


def _load(base: Path, name: str) -> dict:
    path = base / name
    if not path.exists():
        pytest.fail(f"Schema not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------- v1 fixtures ----------
@pytest.fixture
def device_schema():   return _load(V1_DIR, "device.schema.json")

@pytest.fixture
def command_schema():  return _load(V1_DIR, "command.schema.json")

@pytest.fixture
def location_schema(): return _load(V1_DIR, "location.schema.json")

@pytest.fixture
def route_schema():    return _load(V1_DIR, "route.schema.json")

@pytest.fixture
def record_schema():   return _load(V1_DIR, "record.schema.json")


# ---------- v2 fixtures ----------
@pytest.fixture
def algorithm_schema():      return _load(V2_DIR, "algorithm.schema.json")

@pytest.fixture
def provenance_schema():     return _load(V2_DIR, "provenance.schema.json")

@pytest.fixture
def derived_record_schema(): return _load(V2_DIR, "derived_record.schema.json")

@pytest.fixture
def event_schema():          return _load(V2_DIR, "event.schema.json")

@pytest.fixture
def safe_zone_schema():      return _load(V2_DIR, "safe_zone.schema.json")

@pytest.fixture
def alert_schema():          return _load(V2_DIR, "alert.schema.json")


# ---------- canonical v1 example ----------
@pytest.fixture
def valid_device():
    return {
        "device_id": "dev_01H8XYZ",
        "device_name": "Ali's Phone",
        "platform": "android",
        "android_version": "14",
        "app_version": "1.0.0",
        "management_state": "managed",
        "connection_state": "online",
        "battery": {
            "level_percent": 78,
            "charging": False,
            "timestamp": "2026-09-29T10:00:00Z",
        },
        "last_seen": "2026-09-29T10:00:00Z",
        "location_capability": {
            "supported": True,
            "permission_state": "granted",
            "background_supported": True,
        },
        "created_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-29T10:00:00Z",
    }
