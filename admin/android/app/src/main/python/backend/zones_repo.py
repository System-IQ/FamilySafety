"""Safe zones persistence + zone state tracking."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .db import get_conn


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_zone_id() -> str:
    return f"zone_{uuid.uuid4().hex[:20]}"


def _row_to_zone(row) -> dict:
    return {
        "zone_id": row["zone_id"],
        "device_id": row["device_id"],
        "name": row["name"],
        "center": {
            "latitude": row["center_lat"],
            "longitude": row["center_lon"],
        },
        "radius_meters": row["radius_meters"],
        "enabled": bool(row["enabled"]),
        "schedule": (
            json.loads(row["schedule_json"]) if row["schedule_json"] else None
        ),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_zone(
    device_id: str,
    name: str,
    center_lat: float,
    center_lon: float,
    radius_meters: float,
    enabled: bool = True,
    schedule: Optional[dict] = None,
    created_by: Optional[str] = None,
    zone_id: Optional[str] = None,
) -> dict:
    zid = zone_id or new_zone_id()
    now = _utcnow_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO safe_zones
                (zone_id, device_id, name, center_lat, center_lon,
                 radius_meters, enabled, schedule_json, created_by,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                zid,
                device_id,
                name,
                center_lat,
                center_lon,
                radius_meters,
                1 if enabled else 0,
                json.dumps(schedule, sort_keys=True) if schedule else None,
                created_by,
                now,
            ),
        )
    return get_zone(zid)


def get_zone(zone_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM safe_zones WHERE zone_id = ?", (zone_id,)
        ).fetchone()
    return _row_to_zone(row) if row else None


def list_zones(
    device_id: Optional[str] = None,
    enabled_only: bool = False,
) -> list[dict]:
    sql = "SELECT * FROM safe_zones WHERE 1=1"
    params: list[Any] = []
    if device_id:
        sql += " AND device_id = ?"
        params.append(device_id)
    if enabled_only:
        sql += " AND enabled = 1"
    sql += " ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_zone(r) for r in rows]


def update_zone(
    zone_id: str,
    *,
    name: Optional[str] = None,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    radius_meters: Optional[float] = None,
    enabled: Optional[bool] = None,
    schedule: Optional[dict] = None,
    clear_schedule: bool = False,
) -> Optional[dict]:
    current = get_zone(zone_id)
    if current is None:
        return None

    sets: list[str] = []
    params: list[Any] = []

    if name is not None:
        sets.append("name = ?"); params.append(name)
    if center_lat is not None:
        sets.append("center_lat = ?"); params.append(center_lat)
    if center_lon is not None:
        sets.append("center_lon = ?"); params.append(center_lon)
    if radius_meters is not None:
        sets.append("radius_meters = ?"); params.append(radius_meters)
    if enabled is not None:
        sets.append("enabled = ?"); params.append(1 if enabled else 0)
    if clear_schedule:
        sets.append("schedule_json = NULL")
    elif schedule is not None:
        sets.append("schedule_json = ?")
        params.append(json.dumps(schedule, sort_keys=True))

    if not sets:
        return current

    sets.append("updated_at = ?")
    params.append(_utcnow_iso())
    params.append(zone_id)

    with get_conn() as conn:
        conn.execute(
            f"UPDATE safe_zones SET {', '.join(sets)} WHERE zone_id = ?",
            params,
        )
    return get_zone(zone_id)


def delete_zone(zone_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM safe_zones WHERE zone_id = ?", (zone_id,)
        )
        conn.execute(
            "DELETE FROM zone_states WHERE zone_id = ?", (zone_id,)
        )
    return cur.rowcount == 1


# -------- zone state (was_inside per zone) --------

def get_zone_state(zone_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM zone_states WHERE zone_id = ?", (zone_id,)
        ).fetchone()
    if row is None:
        return None
    return {
        "zone_id": row["zone_id"],
        "device_id": row["device_id"],
        "was_inside": bool(row["was_inside"]),
        "last_evaluated_at": row["last_evaluated_at"],
    }


def set_zone_state(
    zone_id: str,
    device_id: str,
    was_inside: bool,
    evaluated_at: str,
) -> None:
    now = _utcnow_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO zone_states
                (zone_id, device_id, was_inside, last_evaluated_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(zone_id) DO UPDATE SET
                was_inside = excluded.was_inside,
                last_evaluated_at = excluded.last_evaluated_at,
                updated_at = excluded.updated_at
            """,
            (zone_id, device_id, 1 if was_inside else 0, evaluated_at, now),
        )
