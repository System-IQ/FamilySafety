"""Contract tests for device.schema.json — real validation, no mocks."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _validate(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


def test_schema_is_valid_draft_2020_12(device_schema):
    Draft202012Validator.check_schema(device_schema)


def test_valid_device_passes(device_schema, valid_device):
    _validate(device_schema, valid_device)


def test_missing_required_field_fails(device_schema, valid_device):
    bad = copy.deepcopy(valid_device)
    del bad["device_id"]
    with pytest.raises(ValidationError):
        _validate(device_schema, bad)


def test_invalid_management_state_fails(device_schema, valid_device):
    bad = copy.deepcopy(valid_device)
    bad["management_state"] = "rooted"
    with pytest.raises(ValidationError):
        _validate(device_schema, bad)


def test_invalid_connection_state_fails(device_schema, valid_device):
    bad = copy.deepcopy(valid_device)
    bad["connection_state"] = "ghost"
    with pytest.raises(ValidationError):
        _validate(device_schema, bad)


def test_battery_out_of_range_fails(device_schema, valid_device):
    bad = copy.deepcopy(valid_device)
    bad["battery"]["level_percent"] = 150
    with pytest.raises(ValidationError):
        _validate(device_schema, bad)


def test_non_utc_timestamp_fails(device_schema, valid_device):
    bad = copy.deepcopy(valid_device)
    bad["last_seen"] = "2026-09-29 10:00:00"
    with pytest.raises(ValidationError):
        _validate(device_schema, bad)


def test_missing_z_suffix_fails(device_schema, valid_device):
    bad = copy.deepcopy(valid_device)
    bad["last_seen"] = "2026-09-29T10:00:00"
    with pytest.raises(ValidationError):
        _validate(device_schema, bad)


def test_invalid_permission_state_fails(device_schema, valid_device):
    bad = copy.deepcopy(valid_device)
    bad["location_capability"]["permission_state"] = "maybe"
    with pytest.raises(ValidationError):
        _validate(device_schema, bad)
