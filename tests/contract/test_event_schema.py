"""Contract tests for event.schema.json (v2)."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _v(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_event():
    return {
        "event_id": "evt_01H8XYZABC",
        "device_id": "dev_01H8XYZ",
        "event_type": "safe_zone_enter",
        "severity": "info",
        "timestamp": "2026-09-29T10:00:00Z",
        "payload": {"zone_id": "zone_home", "zone_name": "Home"},
    }


def test_schema_is_valid(event_schema):
    Draft202012Validator.check_schema(event_schema)


def test_valid_event_passes(event_schema, valid_event):
    _v(event_schema, valid_event)


def test_invalid_event_type_fails(event_schema, valid_event):
    bad = copy.deepcopy(valid_event); bad["event_type"] = "teleport"
    with pytest.raises(ValidationError):
        _v(event_schema, bad)


def test_invalid_severity_fails(event_schema, valid_event):
    bad = copy.deepcopy(valid_event); bad["severity"] = "meh"
    with pytest.raises(ValidationError):
        _v(event_schema, bad)


def test_sos_event_valid(event_schema, valid_event):
    ok = copy.deepcopy(valid_event)
    ok["event_type"] = "sos_triggered"
    ok["severity"] = "critical"
    _v(event_schema, ok)


def test_extra_top_level_field_fails(event_schema, valid_event):
    bad = copy.deepcopy(valid_event); bad["extra"] = 1
    with pytest.raises(ValidationError):
        _v(event_schema, bad)
