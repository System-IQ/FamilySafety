"""Contract tests for derived_record.schema.json (v2)."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _v(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_derived():
    return {
        "record_id": "drec_01H8XYZABC",
        "device_id": "dev_01H8XYZ",
        "record_type": "cleaned_location",
        "timestamp": "2026-09-29T10:00:00Z",
        "payload": {
            "latitude": 33.3152,
            "longitude": 44.3661,
            "accuracy_meters": 6.2,
        },
        "provenance": {
            "source_record_ids": ["rec_001"],
            "algorithm_id": "gps_cleaning",
            "algorithm_version": "1.0.0",
            "calculated_at": "2026-09-29T10:00:01Z",
            "confidence": 0.9,
            "evidence": ["raw point within tolerance"],
        },
        "quality_score": 91.0,
    }


def test_schema_is_valid(derived_record_schema):
    Draft202012Validator.check_schema(derived_record_schema)


def test_valid_derived_passes(derived_record_schema, valid_derived):
    _v(derived_record_schema, valid_derived)


def test_missing_provenance_fails(derived_record_schema, valid_derived):
    bad = copy.deepcopy(valid_derived); del bad["provenance"]
    with pytest.raises(ValidationError):
        _v(derived_record_schema, bad)


def test_quality_score_out_of_range_fails(derived_record_schema, valid_derived):
    bad = copy.deepcopy(valid_derived); bad["quality_score"] = 150
    with pytest.raises(ValidationError):
        _v(derived_record_schema, bad)


def test_invalid_record_type_fails(derived_record_schema, valid_derived):
    bad = copy.deepcopy(valid_derived); bad["record_type"] = "made_up"
    with pytest.raises(ValidationError):
        _v(derived_record_schema, bad)


def test_insufficient_data_block_valid(derived_record_schema, valid_derived):
    ok = copy.deepcopy(valid_derived)
    ok["insufficient_data"] = {
        "is_insufficient": True,
        "reason": "only 1 raw point; cannot compute moving average",
    }
    _v(derived_record_schema, ok)


def test_insufficient_data_missing_reason_fails(derived_record_schema, valid_derived):
    bad = copy.deepcopy(valid_derived)
    bad["insufficient_data"] = {"is_insufficient": True}
    with pytest.raises(ValidationError):
        _v(derived_record_schema, bad)
