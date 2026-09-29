"""Device endpoints — Pydantic + JSON Schema double validation."""
from fastapi import APIRouter, HTTPException, status
from jsonschema import ValidationError as JsonSchemaError

from ..schemas import DeviceIn
from ..storage import get_device, list_devices, upsert_device
from ..validators import validate_contract

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_or_update_device(device: DeviceIn) -> dict:
    # Layer 1 already passed (Pydantic via FastAPI).

    # Layer 2: contract validation
    serialized = device.model_dump(mode="json")
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

    upsert_device(serialized)
    return serialized


@router.get("/{device_id}")
def read_device(device_id: str) -> dict:
    d = get_device(device_id)
    if d is None:
        raise HTTPException(status_code=404, detail="device not found")
    return d


@router.get("")
def list_all() -> dict:
    return {"devices": list_devices()}
