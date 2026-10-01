"""Device repository — persistence layer."""
import json
from typing import Any, Optional

from .db import get_conn


def upsert_device(device: dict[str, Any]) -> None:
    payload = json.dumps(device, default=str, sort_keys=True)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO devices (device_id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                payload    = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (
                device["device_id"],
                payload,
                device["created_at"],
                device["updated_at"],
            ),
        )


def get_device(device_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT payload FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        return json.loads(row["payload"]) if row else None


def list_devices() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT payload FROM devices ORDER BY updated_at DESC"
        ).fetchall()
        return [json.loads(r["payload"]) for r in rows]
