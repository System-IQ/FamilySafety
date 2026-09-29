"""Contract tests for route.schema.json."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _validate(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_route():
    return {
        "route_id": "route_01H8XYZABC",
        "device_id": "dev_01H8XYZ",
        "status": "completed",
        "started_at": "2026-09-29T08:12:00Z",
        "ended_at": "2026-09-29T14:43:00Z",
        "distance_meters": 12450.5,
        "duration_seconds": 23460,
        "raw_point_count": 8421,
        "cleaned_point_count": 8390,
        "integrity_score": 98.7
    }


def test_schema_is_valid_draft_2020_12(route_schema):
    Draft202012Validator.check_schema(route_schema)


def test_valid_route_passes(route_schema, valid_route):
    _validate(route_schema, valid_route)


def test_invalid_status_fails(route_schema, valid_route):
    bad = copy.deepcopy(valid_route)
    bad["status"] = "paused"
    with pytest.raises(ValidationError):
        _validate(route_schema, bad)


def test_negative_distance_fails(route_schema, valid_route):
    bad = copy.deepcopy(valid_route)
    bad["distance_meters"] = -100.0
    with pytest.raises(ValidationError):
        _validate(route_schema, bad)


def test_integrity_over_100_fails(route_schema, valid_route):
    bad = copy.deepcopy(valid_route)
    bad["integrity_score"] = 150.0
    with pytest.raises(ValidationError):
        _validate(route_schema, bad)
