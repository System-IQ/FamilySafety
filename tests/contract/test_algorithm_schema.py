"""Contract tests for algorithm.schema.json (v2)."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _v(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_algorithm():
    return {
        "algorithm_id": "gps_cleaning",
        "name": "GPS Cleaning (jump filter)",
        "version": "1.0.0",
        "input_schema_ref": "location.schema.json",
        "output_schema_ref": "derived_record.schema.json",
        "status": "production",
        "test_status": "passing",
        "created_at": "2026-09-01T00:00:00Z",
    }


def test_schema_is_valid(algorithm_schema):
    Draft202012Validator.check_schema(algorithm_schema)


def test_valid_algorithm_passes(algorithm_schema, valid_algorithm):
    _v(algorithm_schema, valid_algorithm)


def test_invalid_algorithm_id_fails(algorithm_schema, valid_algorithm):
    bad = copy.deepcopy(valid_algorithm); bad["algorithm_id"] = "GPS-Clean!"
    with pytest.raises(ValidationError):
        _v(algorithm_schema, bad)


def test_invalid_version_fails(algorithm_schema, valid_algorithm):
    bad = copy.deepcopy(valid_algorithm); bad["version"] = "1.0"
    with pytest.raises(ValidationError):
        _v(algorithm_schema, bad)


def test_invalid_status_fails(algorithm_schema, valid_algorithm):
    bad = copy.deepcopy(valid_algorithm); bad["status"] = "staging"
    with pytest.raises(ValidationError):
        _v(algorithm_schema, bad)


def test_extra_field_fails(algorithm_schema, valid_algorithm):
    bad = copy.deepcopy(valid_algorithm); bad["hacked"] = True
    with pytest.raises(ValidationError):
        _v(algorithm_schema, bad)
