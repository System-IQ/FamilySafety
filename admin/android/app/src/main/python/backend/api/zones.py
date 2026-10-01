"""/zones endpoints — CRUD + evaluate.

Flow for evaluate:
  read zone -> read prior state -> run pure geofence ->
  write new state -> if entered/exited emit event -> return
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from ..validators import JsonSchemaError

from ..audit_repo import record as audit_record
from ..auth.dependencies import get_current_user
from ..events_repo import insert_event
from ..geofence import evaluate_position
from ..observability import request_meta
from ..schemas_zones import (
    EvaluateRequest,
    EvaluateResponse,
    ZoneCreate,
    ZoneListResponse,
    ZoneOut,
    ZoneUpdate,
)
from .._base_model import dump_json
from ..validators import validate_contract
from ..zones_repo import (
    create_zone,
    delete_zone,
    get_zone,
    get_zone_state,
    list_zones,
    set_zone_state,
    update_zone,
)

router = APIRouter(prefix="/zones", tags=["zones"])


# -------------------- helpers --------------------

def _parse_at_utc(s: Optional[str]) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    raw = s
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        raise HTTPException(status_code=422, detail="invalid at_utc format")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _zone_out(z: dict) -> ZoneOut:
    return ZoneOut(
        zone_id=z["zone_id"],
        device_id=z["device_id"],
        name=z["name"],
        center=z["center"],
        radius_meters=z["radius_meters"],
        enabled=z["enabled"],
        schedule=z.get("schedule"),
        created_at=z["created_at"],
        updated_at=z.get("updated_at"),
    )


def _contract_check(zone: dict) -> None:
    try:
        validate_contract("safe_zone.schema.json", zone)
    except JsonSchemaError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "stage": "contract",
                "message": exc.message,
                "path": list(exc.absolute_path),
            },
        )


# -------------------- CRUD --------------------

@router.post("", status_code=status.HTTP_201_CREATED, response_model=ZoneOut)
def create(
    body: ZoneCreate,
    request: Request,
    current: dict = Depends(get_current_user),
) -> ZoneOut:
    zone = create_zone(
        device_id=body.device_id,
        name=body.name,
        center_lat=body.center.latitude,
        center_lon=body.center.longitude,
        radius_meters=body.radius_meters,
        enabled=body.enabled,
        schedule=dump_json(body.schedule) if body.schedule else None,
        created_by=current["user_id"],
    )
    _contract_check(zone)

    audit_record(
        action="safe_zone.create",
        resource_type="safe_zone",
        resource_id=zone["zone_id"],
        result="success",
        actor_user_id=current["user_id"],
        **request_meta(request),
    )
    return _zone_out(zone)


@router.get("", response_model=ZoneListResponse)
def list_all(
    device_id: Optional[str] = Query(default=None),
    enabled_only: bool = Query(default=False),
    _current: dict = Depends(get_current_user),
) -> ZoneListResponse:
    rows = list_zones(device_id=device_id, enabled_only=enabled_only)
    return ZoneListResponse(zones=[_zone_out(z) for z in rows])


@router.get("/{zone_id}", response_model=ZoneOut)
def read(
    zone_id: str,
    _current: dict = Depends(get_current_user),
) -> ZoneOut:
    z = get_zone(zone_id)
    if z is None:
        raise HTTPException(status_code=404, detail="zone not found")
    return _zone_out(z)


@router.patch("/{zone_id}", response_model=ZoneOut)
def patch(
    zone_id: str,
    body: ZoneUpdate,
    request: Request,
    current: dict = Depends(get_current_user),
) -> ZoneOut:
    if get_zone(zone_id) is None:
        raise HTTPException(status_code=404, detail="zone not found")

    z = update_zone(
        zone_id,
        name=body.name,
        center_lat=body.center.latitude if body.center else None,
        center_lon=body.center.longitude if body.center else None,
        radius_meters=body.radius_meters,
        enabled=body.enabled,
        schedule=dump_json(body.schedule) if body.schedule else None,
        clear_schedule=body.clear_schedule,
    )
    assert z is not None
    _contract_check(z)

    audit_record(
        action="safe_zone.update",
        resource_type="safe_zone",
        resource_id=zone_id,
        result="success",
        actor_user_id=current["user_id"],
        **request_meta(request),
    )
    return _zone_out(z)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    zone_id: str,
    request: Request,
    current: dict = Depends(get_current_user),
) -> None:
    if not delete_zone(zone_id):
        raise HTTPException(status_code=404, detail="zone not found")

    audit_record(
        action="safe_zone.delete",
        resource_type="safe_zone",
        resource_id=zone_id,
        result="success",
        actor_user_id=current["user_id"],
        **request_meta(request),
    )
    return None


# -------------------- evaluate --------------------

@router.post("/{zone_id}/evaluate", response_model=EvaluateResponse)
def evaluate(
    zone_id: str,
    body: EvaluateRequest,
    _current: dict = Depends(get_current_user),
) -> EvaluateResponse:
    zone = get_zone(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="zone not found")

    at_utc = _parse_at_utc(body.at_utc)
    prior = get_zone_state(zone_id)
    was_inside = prior["was_inside"] if prior else False

    result = evaluate_position(
        center_lat=zone["center"]["latitude"],
        center_lon=zone["center"]["longitude"],
        radius_meters=zone["radius_meters"],
        latitude=body.latitude,
        longitude=body.longitude,
        at_utc=at_utc,
        schedule=zone.get("schedule"),
        was_inside=was_inside,
        enabled=zone["enabled"],
    )

    evaluated_at = _iso_utc(at_utc)
    set_zone_state(zone_id, zone["device_id"], result["inside"], evaluated_at)

    event_id: Optional[str] = None
    if result["entered"] or result["exited"]:
        ev_type = "safe_zone_enter" if result["entered"] else "safe_zone_exit"
        ev = insert_event(
            device_id=zone["device_id"],
            event_type=ev_type,
            severity="info",
            timestamp=evaluated_at,
            payload={
                "zone_id": zone_id,
                "zone_name": zone["name"],
                "distance_meters": result["distance_meters"],
                "latitude": body.latitude,
                "longitude": body.longitude,
            },
        )
        event_id = ev["event_id"]

    return EvaluateResponse(
        zone_id=zone_id,
        device_id=zone["device_id"],
        distance_meters=result["distance_meters"],
        within_radius=result["within_radius"],
        within_schedule=result["within_schedule"],
        inside=result["inside"],
        entered=result["entered"],
        exited=result["exited"],
        enabled=result["enabled"],
        was_inside=was_inside,
        evaluated_at=evaluated_at,
        event_id=event_id,
    )
