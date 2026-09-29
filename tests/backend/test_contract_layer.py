"""Cross-check: Pydantic output must always satisfy the JSON Schema contract."""
from backend.schemas import DeviceIn
from backend.validators import validate_contract


def test_pydantic_output_matches_contract(valid_device_payload):
    device = DeviceIn.model_validate(valid_device_payload)
    serialized = device.model_dump(mode="json")
    validate_contract("device.schema.json", serialized)
