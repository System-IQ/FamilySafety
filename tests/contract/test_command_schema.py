"""Contract tests for command.schema.json."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _validate(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_command():
    return {
        "command_id": "cmd_01H8XYZABCDEF",
        "device_id": "dev_01H8XYZ",
        "command_type": "GET_CURRENT_LOCATION",
        "status": "QUEUED",
        "issued_at": "2026-09-29T10:00:00Z",
        "expires_at": "2026-09-29T10:05:00Z",
        "nonce": "a1b2c3d4e5f60718",
        "signature": "sig_abcdef1234567890"
    }


def test_schema_is_valid_draft_2020_12(command_schema):
    Draft202012Validator.check_schema(command_schema)


def test_valid_command_passes(command_schema, valid_command):
    _validate(command_schema, valid_command)


def test_invalid_command_type_fails(command_schema, valid_command):
    bad = copy.deepcopy(valid_command)
    bad["command_type"] = "DELETE_EVERYTHING"
    with pytest.raises(ValidationError):
        _validate(command_schema, bad)


def test_invalid_status_fails(command_schema, valid_command):
    bad = copy.deepcopy(valid_command)
    bad["status"] = "DONE"
    with pytest.raises(ValidationError):
        _validate(command_schema, bad)


def test_short_nonce_fails(command_schema, valid_command):
    bad = copy.deepcopy(valid_command)
    bad["nonce"] = "short"
    with pytest.raises(ValidationError):
        _validate(command_schema, bad)


def test_additional_property_fails(command_schema, valid_command):
    bad = copy.deepcopy(valid_command)
    bad["injected"] = "malicious"
    with pytest.raises(ValidationError):
        _validate(command_schema, bad)
