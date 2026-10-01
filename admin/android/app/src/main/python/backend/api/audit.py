"""/audit endpoints — read-only, authenticated."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..audit_repo import get, list_audit
from ..auth.dependencies import get_current_user
from ..schemas_audit import AuditListResponse, AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditListResponse)
def list_audit_endpoint(
    actor_user_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    _user: dict = Depends(get_current_user),
) -> AuditListResponse:
    rows = list_audit(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        since=since,
        limit=limit,
    )
    return AuditListResponse(audit=[AuditOut(**r) for r in rows])


@router.get("/{audit_id}", response_model=AuditOut)
def read_audit(
    audit_id: str,
    _user: dict = Depends(get_current_user),
) -> AuditOut:
    rec = get(audit_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="audit record not found")
    return AuditOut(**rec)
