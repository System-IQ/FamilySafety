"""Contract tests for location.schema.json."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _validate(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_location():
    return {
        "device_id": "dev_01H8XYZ",
        "latitude": 33.3152,
        "longitude": 44.3661,
        "accuracy_meters": 8.5,
        "altitude_meters": 34.0,
        "speed_mps": 0.0,
        "bearing_degrees": 180.0,
        "timestamp": "2026-09-29T10:00:00Z",
        "provider": "fused"
    }


def test_schema_is_valid_draft_2020_12(location_schema):
    Draft202012Validator.check_schema(location_schema)


def test_valid_location_passes(location_schema, valid_location):
    _validate(location_schema, valid_location)


def test_latitude_out_of_range_fails(location_schema, valid_location):
    bad = copy.deepcopy(valid_location)
    bad["latitude"] = 95.0
    with pytest.raises(ValidationError):
        _validate(location_schema, bad)


def test_longitude_out_of_range_fails(location_schema, valid_location):
    bad = copy.deepcopy(valid_location)
    bad["longitude"] = -200.0
    with pytest.raises(ValidationError):
        _validate(location_schema, bad)


def test_invalid_provider_fails(location_schema, valid_location):
    bad = copy.deepcopy(valid_location)
    bad["provider"] = "telepathy"
    with pytest.raises(ValidationError):
        _validate(location_schema, bad)
