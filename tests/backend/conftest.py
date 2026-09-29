"""Backend test fixtures — isolated temp SQLite per test session."""
import os
import tempfile
from pathlib import Path

import pytest

_TMPDIR = Path(tempfile.mkdtemp(prefix="fs_backend_test_"))
os.environ["FS_ENV"] = "test"
os.environ["FS_DB_PATH"] = str(_TMPDIR / "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402
from backend.db import get_conn  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_db():
    with get_conn() as conn:
        conn.execute("DELETE FROM devices")
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def valid_device_payload():
    return {
        "device_id": "dev_test_001",
        "device_name": "Test Phone",
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
