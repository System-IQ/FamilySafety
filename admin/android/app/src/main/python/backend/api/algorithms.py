"""/algorithms endpoints — registry + lifecycle + audit.

Every state transition is auditable. The lifecycle rules are enforced
in algorithms_repo (single source of truth); this layer just maps
exceptions to HTTP codes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from ..validators import JsonSchemaError

from ..algorithms_repo import (
    AlgorithmError,
    block as repo_block,
    deprecate as repo_deprecate,
    get as repo_get,
    get_production_version,
    list_all,
    promote_to_canary as repo_promote_canary,
    promote_to_production as repo_promote_production,
    promote_to_testing as repo_promote_testing,
    register as repo_register,
    set_test_status as repo_set_test_status,
)
from ..audit_repo import record as audit_record
from ..auth.dependencies import get_current_user
from ..observability import request_meta
from ..schemas_algorithms import (
    AlgorithmListResponse,
    AlgorithmOut,
    PromoteRequest,
    RegisterRequest,
    SetTestStatusRequest,
)
from ..validators import validate_contract

router = APIRouter(prefix="/algorithms", tags=["algorithms"])


def _contract_check(algo: dict) -> None:
    payload = {
        "algorithm_id": algo["algorithm_id"],
        "name": algo["name"],
        "version": algo["version"],
        "input_schema_ref": algo["input_schema_ref"],
        "output_schema_ref": algo["output_schema_ref"],
        "status": algo["status"],
        "test_status": algo["test_status"],
        "created_at": algo["created_at"],
    }
    for k in ("description", "updated_at", "deprecation_reason", "superseded_by"):
        if algo.get(k) is not None:
            payload[k] = algo[k]
    try:
        validate_contract("algorithm.schema.json", payload)
    except JsonSchemaError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "stage": "contract",
                "message": exc.message,
                "path": list(exc.absolute_path),
            },
        )


def _to_out(algo: dict) -> AlgorithmOut:
    return AlgorithmOut(
        algorithm_id=algo["algorithm_id"],
        version=algo["version"],
        name=algo["name"],
        description=algo.get("description"),
        input_schema_ref=algo["input_schema_ref"],
        output_schema_ref=algo["output_schema_ref"],
        status=algo["status"],
        test_status=algo["test_status"],
        created_at=algo["created_at"],
        updated_at=algo.get("updated_at"),
        deprecated_at=algo.get("deprecated_at"),
        deprecation_reason=algo.get("deprecation_reason"),
        superseded_by=algo.get("superseded_by"),
    )


def _get_or_404(algorithm_id: str, version: str) -> dict:
    a = repo_get(algorithm_id, version)
    if a is None:
        raise HTTPException(
            status_code=404,
            detail=f"algorithm {algorithm_id}@{version} not found",
        )
    return a


# -------------------- register --------------------

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AlgorithmOut,
)
def register(
    body: RegisterRequest,
    request: Request,
    current: dict = Depends(get_current_user),
) -> AlgorithmOut:
    try:
        algo = repo_register(
            algorithm_id=body.algorithm_id,
            version=body.version,
            name=body.name,
            input_schema_ref=body.input_schema_ref,
            output_schema_ref=body.output_schema_ref,
            description=body.description,
            test_status=body.test_status,
            created_by=current["user_id"],
        )
    except AlgorithmError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    _contract_check(algo)

    audit_record(
        action="algorithm.register",
        resource_type="algorithm",
        resource_id=f"{algo['algorithm_id']}@{algo['version']}",
        result="success",
        actor_user_id=current["user_id"],
        **request_meta(request),
    )
    return _to_out(algo)


# -------------------- read --------------------

@router.get("", response_model=AlgorithmListResponse)
def list_endpoint(
    algorithm_id: Optional[str] = Query(default=None),
    algo_status: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=1000),
    _current: dict = Depends(get_current_user),
) -> AlgorithmListResponse:
    rows = list_all(algorithm_id=algorithm_id, status=algo_status, limit=limit)
    return AlgorithmListResponse(algorithms=[_to_out(a) for a in rows])


@router.get(
    "/{algorithm_id}/production",
    response_model=AlgorithmOut,
)
def get_production(
    algorithm_id: str,
    _current: dict = Depends(get_current_user),
) -> AlgorithmOut:
    algo = get_production_version(algorithm_id)
    if algo is None:
        raise HTTPException(
            status_code=404,
            detail=f"no production version for {algorithm_id}",
        )
    return _to_out(algo)


@router.get(
    "/{algorithm_id}/{version}",
    response_model=AlgorithmOut,
)
def get_one(
    algorithm_id: str,
    version: str,
    _current: dict = Depends(get_current_user),
) -> AlgorithmOut:
    algo = _get_or_404(algorithm_id, version)
    return _to_out(algo)


# -------------------- mutate --------------------

@router.patch(
    "/{algorithm_id}/{version}/test-status",
    response_model=AlgorithmOut,
)
def set_test_status(
    algorithm_id: str,
    version: str,
    body: SetTestStatusRequest,
    request: Request,
    current: dict = Depends(get_current_user),
) -> AlgorithmOut:
    _get_or_404(algorithm_id, version)
    try:
        algo = repo_set_test_status(algorithm_id, version, body.test_status)
    except AlgorithmError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    audit_record(
        action="algorithm.promote",  # test_status change is part of promotion flow
        resource_type="algorithm",
        resource_id=f"{algorithm_id}@{version}",
        result="success",
        actor_user_id=current["user_id"],
        reason=f"test_status={body.test_status}",
        **request_meta(request),
    )
    return _to_out(algo)


@router.post(
    "/{algorithm_id}/{version}/promote",
    response_model=AlgorithmOut,
)
def promote(
    algorithm_id: str,
    version: str,
    body: PromoteRequest,
    request: Request,
    current: dict = Depends(get_current_user),
) -> AlgorithmOut:
    _get_or_404(algorithm_id, version)

    try:
        if body.target == "testing":
            algo = repo_promote_testing(algorithm_id, version)
        elif body.target == "canary":
            algo = repo_promote_canary(algorithm_id, version)
        elif body.target == "production":
            algo = repo_promote_production(algorithm_id, version)
        elif body.target == "blocked":
            algo = repo_block(algorithm_id, version)
        elif body.target == "deprecated":
            algo = repo_deprecate(
                algorithm_id, version,
                reason=body.reason,
                superseded_by=body.superseded_by,
            )
        else:
            raise HTTPException(status_code=422, detail=f"unknown target: {body.target}")
    except AlgorithmError as exc:
        msg = str(exc)
        # illegal transitions and missing prerequisites -> 409
        raise HTTPException(status_code=409, detail=msg)

    _contract_check(algo)

    audit_action = (
        "algorithm.deprecate" if body.target == "deprecated"
        else "algorithm.promote"
    )
    audit_record(
        action=audit_action,
        resource_type="algorithm",
        resource_id=f"{algorithm_id}@{version}",
        result="success",
        actor_user_id=current["user_id"],
        reason=f"target={body.target}",
        **request_meta(request),
    )
    return _to_out(algo)
