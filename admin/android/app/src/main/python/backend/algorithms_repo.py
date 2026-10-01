"""Algorithms Registry persistence + lifecycle enforcement.

Lifecycle:
    candidate -> testing   (requires test_status=passing)
    testing   -> canary    (requires test_status=passing)
    canary    -> production
    any       -> blocked
    any       -> deprecated (only from production)

Rules:
- (algorithm_id, version) is the natural key.
- Only `production` algorithms may be referenced by derived records.
- Deprecated algorithms stay in DB (never hard-deleted).
"""
import json
from datetime import datetime, timezone
from typing import Any, Optional

from .db import get_conn

_VALID_STATUS = {
    "candidate", "testing", "canary", "production", "deprecated", "blocked",
}
_VALID_TEST_STATUS = {"unknown", "partial", "passing", "failing"}

_TRANSITIONS = {
    "candidate":  {"testing", "blocked", "deprecated"},
    "testing":    {"canary", "blocked", "deprecated"},
    "canary":     {"production", "blocked", "deprecated"},
    "production": {"deprecated"},
    "deprecated": set(),
    "blocked":    set(),
}

# These transitions require test_status == "passing"
_REQUIRE_PASSING = {
    ("candidate", "testing"),
    ("testing", "canary"),
}


class AlgorithmError(ValueError):
    """Invalid registration or transition."""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_algorithm(row) -> dict:
    return {
        "algorithm_id": row["algorithm_id"],
        "version": row["version"],
        "name": row["name"],
        "description": row["description"],
        "input_schema_ref": row["input_schema_ref"],
        "output_schema_ref": row["output_schema_ref"],
        "status": row["status"],
        "test_status": row["test_status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "deprecated_at": row["deprecated_at"],
        "deprecation_reason": row["deprecation_reason"],
        "superseded_by": row["superseded_by"],
        "created_by": row["created_by"],
        "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
    }


def register(
    algorithm_id: str,
    version: str,
    name: str,
    input_schema_ref: str,
    output_schema_ref: str,
    description: Optional[str] = None,
    test_status: str = "unknown",
    created_by: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    if test_status not in _VALID_TEST_STATUS:
        raise AlgorithmError(f"bad test_status: {test_status}")

    now = _utcnow_iso()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM algorithms WHERE algorithm_id = ? AND version = ?",
            (algorithm_id, version),
        ).fetchone()
        if existing:
            raise AlgorithmError(
                f"algorithm {algorithm_id}@{version} already exists"
            )
        conn.execute(
            """
            INSERT INTO algorithms
                (algorithm_id, version, name, description,
                 input_schema_ref, output_schema_ref,
                 status, test_status, created_at, updated_at,
                 created_by, metadata_json)
            VALUES (?, ?, ?, ?,
                    ?, ?,
                    'candidate', ?, ?, NULL,
                    ?, ?)
            """,
            (
                algorithm_id, version, name, description,
                input_schema_ref, output_schema_ref,
                test_status, now,
                created_by,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
    return get(algorithm_id, version)


def get(algorithm_id: str, version: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM algorithms WHERE algorithm_id = ? AND version = ?",
            (algorithm_id, version),
        ).fetchone()
    return _row_to_algorithm(row) if row else None


def list_all(
    algorithm_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    sql = "SELECT * FROM algorithms WHERE 1=1"
    params: list[Any] = []
    if algorithm_id:
        sql += " AND algorithm_id = ?"; params.append(algorithm_id)
    if status:
        sql += " AND status = ?"; params.append(status)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(int(limit))
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_algorithm(r) for r in rows]


def get_production_version(algorithm_id: str) -> Optional[dict]:
    """Return the current production entry for algorithm_id, if any."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM algorithms
            WHERE algorithm_id = ? AND status = 'production'
            ORDER BY created_at DESC LIMIT 1
            """,
            (algorithm_id,),
        ).fetchone()
    return _row_to_algorithm(row) if row else None


def set_test_status(
    algorithm_id: str, version: str, test_status: str
) -> dict:
    if test_status not in _VALID_TEST_STATUS:
        raise AlgorithmError(f"bad test_status: {test_status}")
    if get(algorithm_id, version) is None:
        raise KeyError(f"{algorithm_id}@{version}")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE algorithms
            SET test_status = ?, updated_at = ?
            WHERE algorithm_id = ? AND version = ?
            """,
            (test_status, _utcnow_iso(), algorithm_id, version),
        )
    return get(algorithm_id, version)


def _transition(
    algorithm_id: str,
    version: str,
    target: str,
    *,
    deprecation_reason: Optional[str] = None,
    superseded_by: Optional[str] = None,
) -> dict:
    if target not in _VALID_STATUS:
        raise AlgorithmError(f"unknown status: {target}")
    current = get(algorithm_id, version)
    if current is None:
        raise KeyError(f"{algorithm_id}@{version}")
    if target not in _TRANSITIONS[current["status"]]:
        raise AlgorithmError(
            f"illegal transition: {current['status']} -> {target}"
        )

    if (current["status"], target) in _REQUIRE_PASSING:
        if current["test_status"] != "passing":
            raise AlgorithmError(
                f"transition {current['status']} -> {target} "
                f"requires test_status=passing (currently "
                f"{current['test_status']})"
            )

    now = _utcnow_iso()
    with get_conn() as conn:
        if target == "deprecated":
            conn.execute(
                """
                UPDATE algorithms
                SET status = ?, updated_at = ?, deprecated_at = ?,
                    deprecation_reason = ?, superseded_by = ?
                WHERE algorithm_id = ? AND version = ?
                """,
                (
                    target, now, now,
                    deprecation_reason, superseded_by,
                    algorithm_id, version,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE algorithms
                SET status = ?, updated_at = ?
                WHERE algorithm_id = ? AND version = ?
                """,
                (target, now, algorithm_id, version),
            )
    return get(algorithm_id, version)


def promote_to_testing(algorithm_id: str, version: str) -> dict:
    return _transition(algorithm_id, version, "testing")


def promote_to_canary(algorithm_id: str, version: str) -> dict:
    return _transition(algorithm_id, version, "canary")


def promote_to_production(algorithm_id: str, version: str) -> dict:
    return _transition(algorithm_id, version, "production")


def block(algorithm_id: str, version: str) -> dict:
    return _transition(algorithm_id, version, "blocked")


def deprecate(
    algorithm_id: str,
    version: str,
    reason: Optional[str] = None,
    superseded_by: Optional[str] = None,
) -> dict:
    return _transition(
        algorithm_id, version, "deprecated",
        deprecation_reason=reason,
        superseded_by=superseded_by,
    )
