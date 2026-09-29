"""Contract tests for alert.schema.json (v2)."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _v(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_alert():
    return {
        "alert_id": "alr_01H8XYZABC",
        "device_id": "dev_01H8XYZ",
        "alert_type": "sos",
        "severity": "critical",
        "triggered_at": "2026-09-29T10:00:00Z",
        "state": "new",
        "last_location": {
            "latitude": 33.3152,
            "longitude": 44.3661,
            "accuracy_meters": 8.0,
            "timestamp": "2026-09-29T09:59:55Z",
        },
        "battery_level_percent": 42,
    }


def test_schema_is_valid(alert_schema):
    Draft202012Validator.check_schema(alert_schema)


def test_valid_alert_passes(alert_schema, valid_alert):
    _v(alert_schema, valid_alert)


def test_invalid_alert_type_fails(alert_schema, valid_alert):
    bad = copy.deepcopy(valid_alert); bad["alert_type"] = "surprise"
    with pytest.raises(ValidationError):
        _v(alert_schema, bad)


def test_invalid_state_fails(alert_schema, valid_alert):
    bad = copy.deepcopy(valid_alert); bad["state"] = "solved_by_ai"
    with pytest.raises(ValidationError):
        _v(alert_schema, bad)


def test_acknowledged_with_metadata(alert_schema, valid_alert):
    ok = copy.deepcopy(valid_alert)
    ok["state"] = "acknowledged"
    ok["acknowledged_by"] = "parent_ali"
    ok["acknowledged_at"] = "2026-09-29T10:00:05Z"
    _v(alert_schema, ok)


def test_battery_out_of_range_fails(alert_schema, valid_alert):
    bad = copy.deepcopy(valid_alert); bad["battery_level_percent"] = 150
    with pytest.raises(ValidationError):
        _v(alert_schema, bad)


def test_extra_field_fails(alert_schema, valid_alert):
    bad = copy.deepcopy(valid_alert); bad["injected"] = True
    with pytest.raises(ValidationError):
        _v(alert_schema, bad)
