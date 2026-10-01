"""Derived records persistence with HARD provenance enforcement.

Rules (enforced here, not in the API layer):
1. source_record_ids must be a non-empty list of strings.
2. algorithm_id + algorithm_version MUST exist in algorithms table
   with status='production'. If not -> AlgorithmNotInProduction error.
3. confidence must be in [0.0, 1.0].
4. evidence must be a non-empty list of strings.
5. quality_score must be in [0, 100].
6. If insufficient_data=True, insufficient_reason is mandatory.

Any violation raises DerivedValidationError; API maps to 422/409.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from . import algorithms_repo
from .db import get_conn

_VALID_UNCERTAINTY = {"none", "low", "medium", "high"}


class DerivedValidationError(ValueError):
    """Malformed derived record."""


class AlgorithmNotInProduction(DerivedValidationError):
    """The referenced algorithm is not production — derived record rejected."""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_record_id() -> str:
    return f"drec_{uuid.uuid4().hex[:20]}"


def _row_to_record(row) -> dict:
    return {
        "record_id": row["record_id"],
        "device_id": row["device_id"],
        "record_type": row["record_type"],
        "timestamp": row["timestamp"],
        "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
        "provenance": {
            "source_record_ids": json.loads(row["source_record_ids_json"]),
            "algorithm_id": row["algorithm_id"],
            "algorithm_version": row["algorithm_version"],
            "calculated_at": row["calculated_at"],
            "confidence": row["confidence"],
            "evidence": json.loads(row["evidence_json"]),
            "uncertainty": {
                "level": row["uncertainty_level"],
                "notes": row["uncertainty_notes"],
            },
            "input_hash": row["input_hash"],
        },
        "quality_score": row["quality_score"],
        "insufficient_data": bool(row["insufficient_data"]),
        "insufficient_reason": row["insufficient_reason"],
        "created_at": row["created_at"],
    }


def create(
    device_id: str,
    record_type: str,
    timestamp: str,
    payload: dict[str, Any],
    source_record_ids: list[str],
    algorithm_id: str,
    algorithm_version: str,
    confidence: float,
    evidence: list[str],
    quality_score: float,
    calculated_at: Optional[str] = None,
    uncertainty_level: str = "none",
    uncertainty_notes: Optional[str] = None,
    input_hash: Optional[str] = None,
    insufficient_data: bool = False,
    insufficient_reason: Optional[str] = None,
    created_by: Optional[str] = None,
    record_id: Optional[str] = None,
) -> dict:
    # ---- Rule 1 ----
    if not isinstance(source_record_ids, list) or len(source_record_ids) == 0:
        raise DerivedValidationError("source_record_ids must be a non-empty list")
    for rid in source_record_ids:
        if not isinstance(rid, str) or len(rid) < 4:
            raise DerivedValidationError(
                f"invalid source_record_id: {rid!r} (min length 4)"
            )

    # ---- Rule 2: algorithm must be in production ----
    prod = algorithms_repo.get_production_version(algorithm_id)
    if prod is None:
        raise AlgorithmNotInProduction(
            f"algorithm {algorithm_id} has no production version"
        )
    if prod["version"] != algorithm_version:
        raise AlgorithmNotInProduction(
            f"algorithm {algorithm_id}@{algorithm_version} is not production "
            f"(current production: {prod['version']})"
        )

    # ---- Rule 3 ----
    if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
        raise DerivedValidationError("confidence must be in [0.0, 1.0]")

    # ---- Rule 4 ----
    if not isinstance(evidence, list) or len(evidence) == 0:
        raise DerivedValidationError("evidence must be a non-empty list")
    for ev in evidence:
        if not isinstance(ev, str) or len(ev) < 3:
            raise DerivedValidationError(
                f"evidence entries must be strings with length >= 3"
            )

    # ---- Rule 5 ----
    if not isinstance(quality_score, (int, float)) or not (0.0 <= float(quality_score) <= 100.0):
        raise DerivedValidationError("quality_score must be in [0, 100]")

    # ---- Rule 6 ----
    if insufficient_data:
        if not insufficient_reason or len(insufficient_reason) < 3:
            raise DerivedValidationError(
                "insufficient_reason is required when insufficient_data=True"
            )

    # ---- uncertainty level ----
    if uncertainty_level not in _VALID_UNCERTAINTY:
        raise DerivedValidationError(
            f"uncertainty.level must be one of {sorted(_VALID_UNCERTAINTY)}"
        )

    rid = record_id or new_record_id()
    now = _utcnow_iso()
    calc_at = calculated_at or now

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO derived_records
                (record_id, device_id, record_type, timestamp, payload_json,
                 source_record_ids_json, algorithm_id, algorithm_version,
                 calculated_at, confidence, evidence_json,
                 uncertainty_level, uncertainty_notes, input_hash,
                 quality_score, insufficient_data, insufficient_reason,
                 created_by, created_at)
            VALUES (?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?)
            """,
            (
                rid, device_id, record_type, timestamp,
                json.dumps(payload or {}, sort_keys=True),
                json.dumps(source_record_ids),
                algorithm_id, algorithm_version,
                calc_at, float(confidence),
                json.dumps(evidence),
                uncertainty_level, uncertainty_notes, input_hash,
                float(quality_score),
                1 if insufficient_data else 0,
                insufficient_reason,
                created_by, now,
            ),
        )
    return get(rid)


def get(record_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM derived_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
    return _row_to_record(row) if row else None


def list_all(
    device_id: Optional[str] = None,
    record_type: Optional[str] = None,
    algorithm_id: Optional[str] = None,
    since: Optional[str] = None,
    min_quality: Optional[float] = None,
    include_insufficient: bool = True,
    limit: int = 200,
) -> list[dict]:
    sql = "SELECT * FROM derived_records WHERE 1=1"
    params: list[Any] = []
    if device_id:
        sql += " AND device_id = ?"; params.append(device_id)
    if record_type:
        sql += " AND record_type = ?"; params.append(record_type)
    if algorithm_id:
        sql += " AND algorithm_id = ?"; params.append(algorithm_id)
    if since:
        sql += " AND timestamp >= ?"; params.append(since)
    if min_quality is not None:
        sql += " AND quality_score >= ?"; params.append(float(min_quality))
    if not include_insufficient:
        sql += " AND insufficient_data = 0"
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(int(limit))
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_record(r) for r in rows]


def count(
    device_id: Optional[str] = None,
    record_type: Optional[str] = None,
) -> int:
    sql = "SELECT COUNT(*) AS c FROM derived_records WHERE 1=1"
    params: list[Any] = []
    if device_id:
        sql += " AND device_id = ?"; params.append(device_id)
    if record_type:
        sql += " AND record_type = ?"; params.append(record_type)
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
    return int(row["c"])
