"""/derived endpoints — provenance-enforced derived records."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from jsonschema import ValidationError as JsonSchemaError

from ..audit_repo import record as audit_record
from ..auth.dependencies import get_current_user
from ..derived_repo import (
    AlgorithmNotInProduction,
    DerivedValidationError,
    create as repo_create,
    get as repo_get,
    list_all as repo_list,
)
from ..observability import request_meta
from ..schemas_derived import (
    DerivedCreate,
    DerivedListResponse,
    DerivedOut,
)
from ..validators import validate_contract

router = APIRouter(prefix="/derived", tags=["derived"])


def _contract_check(rec: dict) -> None:
    payload = {
        "record_id": rec["record_id"],
        "device_id": rec["device_id"],
        "record_type": rec["record_type"],
        "timestamp": rec["timestamp"],
        "payload": rec["payload"],
        "provenance": rec["provenance"],
        "quality_score": rec["quality_score"],
    }
    if rec.get("insufficient_data"):
        payload["insufficient_data"] = {
            "is_insufficient": True,
            "reason": rec["insufficient_reason"],
        }
    try:
        validate_contract("derived_record.schema.json", payload)
    except JsonSchemaError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "stage": "contract",
                "message": exc.message,
                "path": list(exc.absolute_path),
            },
        )


def _to_out(rec: dict) -> DerivedOut:
    return DerivedOut(
        record_id=rec["record_id"],
        device_id=rec["device_id"],
        record_type=rec["record_type"],
        timestamp=rec["timestamp"],
        payload=rec["payload"],
        provenance=rec["provenance"],
        quality_score=rec["quality_score"],
        insufficient_data=rec["insufficient_data"],
        insufficient_reason=rec.get("insufficient_reason"),
        created_at=rec["created_at"],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DerivedOut)
def create(
    body: DerivedCreate,
    request: Request,
    current: dict = Depends(get_current_user),
) -> DerivedOut:
    prov = body.provenance
    uncertainty = prov.uncertainty or None

    try:
        rec = repo_create(
            device_id=body.device_id,
            record_type=body.record_type,
            timestamp=body.timestamp,
            payload=body.payload,
            source_record_ids=prov.source_record_ids,
            algorithm_id=prov.algorithm_id,
            algorithm_version=prov.algorithm_version,
            confidence=prov.confidence,
            evidence=prov.evidence,
            quality_score=body.quality_score,
            calculated_at=prov.calculated_at,
            uncertainty_level=uncertainty.level if uncertainty else "none",
            uncertainty_notes=uncertainty.notes if uncertainty else None,
            input_hash=prov.input_hash,
            insufficient_data=body.insufficient_data,
            insufficient_reason=body.insufficient_reason,
            created_by=current["user_id"],
        )
    except AlgorithmNotInProduction as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DerivedValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    _contract_check(rec)

    audit_record(
        action="derived.create",
        resource_type="derived",
        resource_id=rec["record_id"],
        result="success",
        actor_user_id=current["user_id"],
        reason=f"{rec['record_type']} via {prov.algorithm_id}@{prov.algorithm_version}",
        **request_meta(request),
    )
    return _to_out(rec)


@router.get("", response_model=DerivedListResponse)
def list_endpoint(
    device_id: Optional[str] = Query(default=None),
    record_type: Optional[str] = Query(default=None),
    algorithm_id: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    min_quality: Optional[float] = Query(default=None, ge=0.0, le=100.0),
    include_insufficient: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=1000),
    _current: dict = Depends(get_current_user),
) -> DerivedListResponse:
    rows = repo_list(
        device_id=device_id,
        record_type=record_type,
        algorithm_id=algorithm_id,
        since=since,
        min_quality=min_quality,
        include_insufficient=include_insufficient,
        limit=limit,
    )
    return DerivedListResponse(records=[_to_out(r) for r in rows])


@router.get("/{record_id}", response_model=DerivedOut)
def read(
    record_id: str,
    _current: dict = Depends(get_current_user),
) -> DerivedOut:
    rec = repo_get(record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="derived record not found")
    return _to_out(rec)
