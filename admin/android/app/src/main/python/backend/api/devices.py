"""Device endpoints — double validation + audit on writes."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from ..validators import JsonSchemaError
from .._base_model import dump_json

from ..audit_repo import record as audit_record
from ..auth.dependencies import get_current_user
from ..observability import request_meta
from ..schemas import DeviceIn
from ..storage import get_device, list_devices, upsert_device
from ..validators import validate_contract

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_or_update_device(
    device: DeviceIn,
    request: Request,
    current: dict = Depends(get_current_user),
) -> dict:
    serialized = dump_json(device)
    try:
        validate_contract("device.schema.json", serialized)
    except JsonSchemaError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "stage": "contract",
                "message": exc.message,
                "path": list(exc.absolute_path),
            },
        )

    existed = get_device(serialized["device_id"]) is not None
    upsert_device(serialized)

    audit_record(
        action="device.update" if existed else "device.create",
        resource_type="device",
        result="success",
        actor_user_id=current["user_id"],
        resource_id=serialized["device_id"],
        **request_meta(request),
    )
    return serialized


@router.get("/{device_id}")
def read_device(
    device_id: str,
    current: dict = Depends(get_current_user),
) -> dict:
    d = get_device(device_id)
    if d is None:
        raise HTTPException(status_code=404, detail="device not found")
    return d


@router.get("")
def list_all(current: dict = Depends(get_current_user)) -> dict:
    return {"devices": list_devices()}
