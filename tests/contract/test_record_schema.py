"""Contract tests for record.schema.json."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _validate(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_record():
    return {
        "record_id": "rec_01H8XYZABC",
        "device_id": "dev_01H8XYZ",
        "sequence_number": 42,
        "timestamp": "2026-09-29T10:00:00Z",
        "payload_hash": "a" * 64,
        "previous_hash": "b" * 64,
        "signature": "sig_abcdef1234567890",
        "sync_state": "queued"
    }


def test_schema_is_valid_draft_2020_12(record_schema):
    Draft202012Validator.check_schema(record_schema)


def test_valid_record_passes(record_schema, valid_record):
    _validate(record_schema, valid_record)


def test_negative_sequence_fails(record_schema, valid_record):
    bad = copy.deepcopy(valid_record)
    bad["sequence_number"] = -1
    with pytest.raises(ValidationError):
        _validate(record_schema, bad)


def test_short_payload_hash_fails(record_schema, valid_record):
    bad = copy.deepcopy(valid_record)
    bad["payload_hash"] = "tooshort"
    with pytest.raises(ValidationError):
        _validate(record_schema, bad)


def test_invalid_sync_state_fails(record_schema, valid_record):
    bad = copy.deepcopy(valid_record)
    bad["sync_state"] = "unknown"
    with pytest.raises(ValidationError):
        _validate(record_schema, bad)
