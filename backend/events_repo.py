"""Events timeline persistence. Domain events (device/SOS/geofence/etc)."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .db import get_conn


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:20]}"


def insert_event(
    device_id: str,
    event_type: str,
    severity: str,
    timestamp: str,
    payload: Optional[dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    event_id: Optional[str] = None,
) -> dict:
    eid = event_id or new_event_id()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO events
                (event_id, device_id, event_type, severity, timestamp,
                 payload_json, correlation_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eid,
                device_id,
                event_type,
                severity,
                timestamp,
                json.dumps(payload or {}, sort_keys=True),
                correlation_id,
                _utcnow_iso(),
            ),
        )
    return {
        "event_id": eid,
        "device_id": device_id,
        "event_type": event_type,
        "severity": severity,
        "timestamp": timestamp,
        "payload": payload or {},
        "correlation_id": correlation_id,
    }


def get_event(event_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_event(row)


def list_events(
    device_id: Optional[str] = None,
    event_type: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    sql = "SELECT * FROM events WHERE 1=1"
    params: list[Any] = []
    if device_id:
        sql += " AND device_id = ?"
        params.append(device_id)
    if event_type:
        sql += " AND event_type = ?"
        params.append(event_type)
    if since:
        sql += " AND timestamp >= ?"
        params.append(since)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(int(limit))
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_event(r) for r in rows]


def count_events(device_id: Optional[str] = None) -> int:
    with get_conn() as conn:
        if device_id:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM events WHERE device_id = ?",
                (device_id,),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()
    return int(row["c"])


def _row_to_event(row) -> dict:
    return {
        "event_id": row["event_id"],
        "device_id": row["device_id"],
        "event_type": row["event_type"],
        "severity": row["severity"],
        "timestamp": row["timestamp"],
        "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
        "correlation_id": row["correlation_id"],
    }
