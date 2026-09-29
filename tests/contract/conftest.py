"""Shared fixtures for contract tests."""
from pathlib import Path
import json
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "shared" / "contracts" / "v1"


def _load_schema(name: str) -> dict:
    path = CONTRACTS_DIR / name
    if not path.exists():
        pytest.fail(f"Schema not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def device_schema():
    return _load_schema("device.schema.json")


@pytest.fixture
def command_schema():
    return _load_schema("command.schema.json")


@pytest.fixture
def location_schema():
    return _load_schema("location.schema.json")


@pytest.fixture
def route_schema():
    return _load_schema("route.schema.json")


@pytest.fixture
def record_schema():
    return _load_schema("record.schema.json")


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
            "timestamp": "2026-09-29T10:00:00Z"
        },
        "last_seen": "2026-09-29T10:00:00Z",
        "location_capability": {
            "supported": True,
            "permission_state": "granted",
            "background_supported": True
        },
        "created_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-29T10:00:00Z"
    }
