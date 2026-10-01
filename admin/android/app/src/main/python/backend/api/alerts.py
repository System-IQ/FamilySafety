"""/alerts endpoints — CRUD + state machine + audit.

All state changes go through alerts_repo (single source of truth).
Invalid transitions -> 409 Conflict with the reason.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from ..validators import JsonSchemaError

from ..alerts_repo import (
    AlertTransitionError,
    acknowledge as repo_acknowledge,
    create_alert,
    dismiss as repo_dismiss,
    get_alert,
    list_alerts,
    resolve as repo_resolve,
)
from ..audit_repo import record as audit_record
from ..auth.dependencies import get_current_user
from ..observability import request_meta
from ..schemas_alerts import (
    AcknowledgeRequest,
    AlertCreate,
    AlertListResponse,
    AlertOut,
    DismissRequest,
    ResolveRequest,
)
from ..validators import validate_contract

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _contract_check(alert: dict) -> None:
    """Strip DB-only fields, then validate against alert.schema.json."""
    payload = {
        "alert_id": alert["alert_id"],
        "device_id": alert["device_id"],
        "alert_type": alert["alert_type"],
        "severity": alert["severity"],
        "triggered_at": alert["triggered_at"],
        "state": alert["state"],
    }
    for k in ("note", "last_location", "battery_level_percent",
              "acknowledged_by", "acknowledged_at", "resolved_at"):
        if alert.get(k) is not None:
            payload[k] = alert[k]
    try:
        validate_contract("alert.schema.json", payload)
    except JsonSchemaError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "stage": "contract",
                "message": exc.message,
                "path": list(exc.absolute_path),
            },
        )


def _alert_out(alert: dict) -> AlertOut:
    return AlertOut(
        alert_id=alert["alert_id"],
        device_id=alert["device_id"],
        alert_type=alert["alert_type"],
        severity=alert["severity"],
        state=alert["state"],
        triggered_at=alert["triggered_at"],
        note=alert.get("note"),
        last_location=alert.get("last_location"),
        battery_level_percent=alert.get("battery_level_percent"),
        acknowledged_by=alert.get("acknowledged_by"),
        acknowledged_at=alert.get("acknowledged_at"),
        resolved_at=alert.get("resolved_at"),
        dismissed_at=alert.get("dismissed_at"),
        dismiss_reason=alert.get("dismiss_reason"),
        created_at=alert["created_at"],
        updated_at=alert["updated_at"],
    )


# -------------------- create --------------------

@router.post("", status_code=status.HTTP_201_CREATED, response_model=AlertOut)
def create(
    body: AlertCreate,
    request: Request,
    current: dict = Depends(get_current_user),
) -> AlertOut:
    alert = create_alert(
        device_id=body.device_id,
        alert_type=body.alert_type,
        severity=body.severity,
        triggered_at=body.triggered_at,
        triggered_by_user_id=current["user_id"],
        note=body.note,
        last_location=body.last_location.model_dump() if body.last_location else None,
        battery_level_percent=body.battery_level_percent,
    )
    _contract_check(alert)

    audit_record(
        action="alert.create",
        resource_type="alert",
        resource_id=alert["alert_id"],
        result="success",
        actor_user_id=current["user_id"],
        **request_meta(request),
    )
    return _alert_out(alert)


# -------------------- read --------------------

@router.get("", response_model=AlertListResponse)
def list_all(
    device_id: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    alert_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    _current: dict = Depends(get_current_user),
) -> AlertListResponse:
    rows = list_alerts(
        device_id=device_id,
        state=state,
        alert_type=alert_type,
        severity=severity,
        since=since,
        limit=limit,
    )
    return AlertListResponse(alerts=[_alert_out(a) for a in rows])


@router.get("/{alert_id}", response_model=AlertOut)
def read(
    alert_id: str,
    _current: dict = Depends(get_current_user),
) -> AlertOut:
    alert = get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return _alert_out(alert)


# -------------------- state changes --------------------

@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge(
    alert_id: str,
    body: AcknowledgeRequest,
    request: Request,
    current: dict = Depends(get_current_user),
) -> AlertOut:
    try:
        alert = repo_acknowledge(alert_id, current["user_id"])
    except KeyError:
        raise HTTPException(status_code=404, detail="alert not found")
    except AlertTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    audit_record(
        action="alert.acknowledge",
        resource_type="alert",
        resource_id=alert_id,
        result="success",
        actor_user_id=current["user_id"],
        **request_meta(request),
    )
    return _alert_out(alert)


@router.post("/{alert_id}/resolve", response_model=AlertOut)
def resolve(
    alert_id: str,
    body: ResolveRequest,
    request: Request,
    current: dict = Depends(get_current_user),
) -> AlertOut:
    try:
        alert = repo_resolve(alert_id, current["user_id"])
    except KeyError:
        raise HTTPException(status_code=404, detail="alert not found")
    except AlertTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    audit_record(
        action="alert.resolve",
        resource_type="alert",
        resource_id=alert_id,
        result="success",
        actor_user_id=current["user_id"],
        **request_meta(request),
    )
    return _alert_out(alert)


@router.post("/{alert_id}/dismiss", response_model=AlertOut)
def dismiss(
    alert_id: str,
    body: DismissRequest,
    request: Request,
    current: dict = Depends(get_current_user),
) -> AlertOut:
    try:
        alert = repo_dismiss(alert_id, current["user_id"], reason=body.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="alert not found")
    except AlertTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    audit_record(
        action="alert.dismiss",
        resource_type="alert",
        resource_id=alert_id,
        result="success",
        actor_user_id=current["user_id"],
        **request_meta(request),
    )
    return _alert_out(alert)
