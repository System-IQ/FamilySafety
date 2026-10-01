"""Audit trail persistence. Who did what, when, from where."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .db import get_conn


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_audit_id() -> str:
    return f"aud_{uuid.uuid4().hex[:20]}"


def record(
    action: str,
    resource_type: str,
    result: str,
    actor_user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    timestamp: Optional[str] = None,
    audit_id: Optional[str] = None,
) -> dict:
    aid = audit_id or new_audit_id()
    ts = timestamp or _utcnow_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_events
                (audit_id, actor_user_id, action, resource_type, resource_id,
                 result, reason, ip_address, user_agent, timestamp,
                 metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                aid,
                actor_user_id,
                action,
                resource_type,
                resource_id,
                result,
                reason,
                ip_address,
                user_agent,
                ts,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
    return {
        "audit_id": aid,
        "actor_user_id": actor_user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "result": result,
        "timestamp": ts,
    }


def get(audit_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM audit_events WHERE audit_id = ?", (audit_id,)
        ).fetchone()
    return _row_to_audit(row) if row else None


def list_audit(
    actor_user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    sql = "SELECT * FROM audit_events WHERE 1=1"
    params: list[Any] = []
    if actor_user_id:
        sql += " AND actor_user_id = ?"
        params.append(actor_user_id)
    if action:
        sql += " AND action = ?"
        params.append(action)
    if resource_type:
        sql += " AND resource_type = ?"
        params.append(resource_type)
    if resource_id:
        sql += " AND resource_id = ?"
        params.append(resource_id)
    if since:
        sql += " AND timestamp >= ?"
        params.append(since)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(int(limit))
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_audit(r) for r in rows]


def count_audit(actor_user_id: Optional[str] = None) -> int:
    with get_conn() as conn:
        if actor_user_id:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM audit_events WHERE actor_user_id = ?",
                (actor_user_id,),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) AS c FROM audit_events").fetchone()
    return int(row["c"])


def _row_to_audit(row) -> dict:
    return {
        "audit_id": row["audit_id"],
        "actor_user_id": row["actor_user_id"],
        "action": row["action"],
        "resource_type": row["resource_type"],
        "resource_id": row["resource_id"],
        "result": row["result"],
        "reason": row["reason"],
        "ip_address": row["ip_address"],
        "user_agent": row["user_agent"],
        "timestamp": row["timestamp"],
        "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
    }
