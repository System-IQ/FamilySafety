"""Contract tests for safe_zone.schema.json (v2)."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _v(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_zone():
    return {
        "zone_id": "zone_home_01",
        "device_id": "dev_01H8XYZ",
        "name": "Home",
        "center": {"latitude": 33.3152, "longitude": 44.3661},
        "radius_meters": 150.0,
        "enabled": True,
        "schedule": {
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "start_time": "14:00",
            "end_time": "07:00",
        },
        "created_at": "2026-09-01T00:00:00Z",
    }


def test_schema_is_valid(safe_zone_schema):
    Draft202012Validator.check_schema(safe_zone_schema)


def test_valid_zone_passes(safe_zone_schema, valid_zone):
    _v(safe_zone_schema, valid_zone)


def test_radius_too_small_fails(safe_zone_schema, valid_zone):
    bad = copy.deepcopy(valid_zone); bad["radius_meters"] = 5
    with pytest.raises(ValidationError):
        _v(safe_zone_schema, bad)


def test_radius_too_large_fails(safe_zone_schema, valid_zone):
    bad = copy.deepcopy(valid_zone); bad["radius_meters"] = 100_000
    with pytest.raises(ValidationError):
        _v(safe_zone_schema, bad)


def test_invalid_day_fails(safe_zone_schema, valid_zone):
    bad = copy.deepcopy(valid_zone); bad["schedule"]["days"] = ["funday"]
    with pytest.raises(ValidationError):
        _v(safe_zone_schema, bad)


def test_invalid_time_format_fails(safe_zone_schema, valid_zone):
    bad = copy.deepcopy(valid_zone); bad["schedule"]["start_time"] = "25:99"
    with pytest.raises(ValidationError):
        _v(safe_zone_schema, bad)


def test_lat_out_of_range_fails(safe_zone_schema, valid_zone):
    bad = copy.deepcopy(valid_zone); bad["center"]["latitude"] = 91.0
    with pytest.raises(ValidationError):
        _v(safe_zone_schema, bad)
