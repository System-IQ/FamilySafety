"""/events endpoints — real DB, authenticated, contract-validated."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from jsonschema import ValidationError as JsonSchemaError

from ..auth.dependencies import get_current_user
from ..events_repo import get_event, insert_event, list_events
from ..schemas_events import EventCreate, EventListResponse, EventOut
from ..validators import validate_contract

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=EventOut)
def create_event(
    body: EventCreate,
    _user: dict = Depends(get_current_user),
) -> EventOut:
    rec = insert_event(
        device_id=body.device_id,
        event_type=body.event_type,
        severity=body.severity,
        timestamp=body.timestamp,
        payload=body.payload,
        correlation_id=body.correlation_id,
    )

    # Layer 2 — the full event must satisfy the v2 contract
    try:
        validate_contract("event.schema.json", rec)
    except JsonSchemaError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "stage": "contract",
                "message": exc.message,
                "path": list(exc.absolute_path),
            },
        )

    return EventOut(**rec)


@router.get("", response_model=EventListResponse)
def list_events_endpoint(
    device_id: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    _user: dict = Depends(get_current_user),
) -> EventListResponse:
    rows = list_events(
        device_id=device_id,
        event_type=event_type,
        since=since,
        limit=limit,
    )
    return EventListResponse(events=[EventOut(**r) for r in rows])


@router.get("/{event_id}", response_model=EventOut)
def read_event(
    event_id: str,
    _user: dict = Depends(get_current_user),
) -> EventOut:
    rec = get_event(event_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="event not found")
    return EventOut(**rec)
