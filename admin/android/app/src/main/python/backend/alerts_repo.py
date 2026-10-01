"""Alerts persistence + state machine.

State machine (enforced here, not in the API layer):
    new          -> acknowledged | resolved | dismissed
    acknowledged -> resolved | dismissed
    resolved     -> (terminal)
    dismissed    -> (terminal)
    expired      -> (terminal)

Any invalid transition raises ValueError; the API maps it to 409.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .db import get_conn

_VALID_STATES = {"new", "acknowledged", "resolved", "dismissed", "expired"}
_TERMINAL = {"resolved", "dismissed", "expired"}

_TRANSITIONS = {
    "new":          {"acknowledged", "resolved", "dismissed", "expired"},
    "acknowledged": {"resolved", "dismissed", "expired"},
    "resolved":     set(),
    "dismissed":    set(),
    "expired":      set(),
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_alert_id() -> str:
    return f"alr_{uuid.uuid4().hex[:20]}"


class AlertTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""


def _row_to_alert(row) -> dict:
    alert = {
        "alert_id": row["alert_id"],
        "device_id": row["device_id"],
        "alert_type": row["alert_type"],
        "severity": row["severity"],
        "state": row["state"],
        "triggered_at": row["triggered_at"],
        "note": row["note"],
        "battery_level_percent": row["battery_level_percent"],
        "acknowledged_by": row["acknowledged_by"],
        "acknowledged_at": row["acknowledged_at"],
        "resolved_at": row["resolved_at"],
        "dismissed_at": row["dismissed_at"],
        "dismiss_reason": row["dismiss_reason"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if row["last_latitude"] is not None and row["last_longitude"] is not None:
        loc = {
            "latitude": row["last_latitude"],
            "longitude": row["last_longitude"],
            "timestamp": row["last_location_ts"],
        }
        if row["last_accuracy_meters"] is not None:
            loc["accuracy_meters"] = row["last_accuracy_meters"]
        alert["last_location"] = loc
    else:
        alert["last_location"] = None
    if row["provenance_json"]:
        alert["provenance"] = json.loads(row["provenance_json"])
    return alert


def create_alert(
    device_id: str,
    alert_type: str,
    severity: str,
    triggered_at: Optional[str] = None,
    triggered_by_user_id: Optional[str] = None,
    note: Optional[str] = None,
    last_location: Optional[dict] = None,
    battery_level_percent: Optional[int] = None,
    provenance: Optional[dict] = None,
    alert_id: Optional[str] = None,
) -> dict:
    aid = alert_id or new_alert_id()
    now = _utcnow_iso()
    ts = triggered_at or now

    lat = lon = acc = loc_ts = None
    if last_location:
        lat = last_location.get("latitude")
        lon = last_location.get("longitude")
        acc = last_location.get("accuracy_meters")
        loc_ts = last_location.get("timestamp")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO alerts
                (alert_id, device_id, alert_type, severity, state,
                 triggered_at, triggered_by_user_id, note,
                 last_latitude, last_longitude, last_accuracy_meters,
                 last_location_ts, battery_level_percent,
                 acknowledged_by, acknowledged_at, resolved_at,
                 dismissed_at, dismiss_reason, provenance_json,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, 'new',
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    NULL, NULL, NULL,
                    NULL, NULL, ?,
                    ?, ?)
            """,
            (
                aid, device_id, alert_type, severity,
                ts, triggered_by_user_id, note,
                lat, lon, acc,
                loc_ts, battery_level_percent,
                json.dumps(provenance, sort_keys=True) if provenance else None,
                now, now,
            ),
        )
    return get_alert(aid)


def get_alert(alert_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)
        ).fetchone()
    return _row_to_alert(row) if row else None


def list_alerts(
    device_id: Optional[str] = None,
    state: Optional[str] = None,
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    sql = "SELECT * FROM alerts WHERE 1=1"
    params: list[Any] = []
    if device_id:
        sql += " AND device_id = ?"; params.append(device_id)
    if state:
        sql += " AND state = ?"; params.append(state)
    if alert_type:
        sql += " AND alert_type = ?"; params.append(alert_type)
    if severity:
        sql += " AND severity = ?"; params.append(severity)
    if since:
        sql += " AND triggered_at >= ?"; params.append(since)
    sql += " ORDER BY triggered_at DESC LIMIT ?"
    params.append(int(limit))
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_alert(r) for r in rows]


def count_alerts(
    device_id: Optional[str] = None,
    state: Optional[str] = None,
) -> int:
    sql = "SELECT COUNT(*) AS c FROM alerts WHERE 1=1"
    params: list[Any] = []
    if device_id:
        sql += " AND device_id = ?"; params.append(device_id)
    if state:
        sql += " AND state = ?"; params.append(state)
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
    return int(row["c"])


def _apply_transition(
    alert_id: str,
    target: str,
    extra_sets: list[str],
    extra_params: list[Any],
) -> dict:
    current = get_alert(alert_id)
    if current is None:
        raise KeyError(alert_id)
    if target not in _VALID_STATES:
        raise AlertTransitionError(f"unknown target state: {target}")
    if target not in _TRANSITIONS[current["state"]]:
        raise AlertTransitionError(
            f"illegal transition: {current['state']} -> {target}"
        )

    sets = ["state = ?"] + extra_sets + ["updated_at = ?"]
    params: list[Any] = [target] + extra_params + [_utcnow_iso(), alert_id]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE alerts SET {', '.join(sets)} WHERE alert_id = ?",
            params,
        )
    return get_alert(alert_id)


def acknowledge(alert_id: str, actor_user_id: str) -> dict:
    return _apply_transition(
        alert_id,
        "acknowledged",
        ["acknowledged_by = ?", "acknowledged_at = ?"],
        [actor_user_id, _utcnow_iso()],
    )


def resolve(alert_id: str, actor_user_id: Optional[str] = None) -> dict:
    return _apply_transition(
        alert_id,
        "resolved",
        ["resolved_at = ?"],
        [_utcnow_iso()],
    )


def dismiss(
    alert_id: str,
    actor_user_id: str,
    reason: Optional[str] = None,
) -> dict:
    return _apply_transition(
        alert_id,
        "dismissed",
        ["dismissed_at = ?", "dismiss_reason = ?"],
        [_utcnow_iso(), reason],
    )


def expire(alert_id: str) -> dict:
    """System-driven expiration (e.g. cleanup job)."""
    return _apply_transition(
        alert_id,
        "expired",
        [],
        [],
    )
