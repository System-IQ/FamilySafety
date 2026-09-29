"""Contract tests for provenance.schema.json (v2)."""
import copy
import pytest
from jsonschema import Draft202012Validator, ValidationError, FormatChecker

FC = FormatChecker()


def _v(schema, instance):
    return Draft202012Validator(schema, format_checker=FC).validate(instance)


@pytest.fixture
def valid_provenance():
    return {
        "source_record_ids": ["rec_001", "rec_002", "rec_003"],
        "algorithm_id": "gps_cleaning",
        "algorithm_version": "1.0.0",
        "calculated_at": "2026-09-29T10:00:00Z",
        "confidence": 0.87,
        "evidence": [
            "3 source points used",
            "jump distance > threshold removed",
        ],
        "uncertainty": {"level": "low", "notes": None},
    }


def test_schema_is_valid(provenance_schema):
    Draft202012Validator.check_schema(provenance_schema)


def test_valid_provenance_passes(provenance_schema, valid_provenance):
    _v(provenance_schema, valid_provenance)


def test_empty_source_ids_fails(provenance_schema, valid_provenance):
    bad = copy.deepcopy(valid_provenance); bad["source_record_ids"] = []
    with pytest.raises(ValidationError):
        _v(provenance_schema, bad)


def test_confidence_over_one_fails(provenance_schema, valid_provenance):
    bad = copy.deepcopy(valid_provenance); bad["confidence"] = 1.5
    with pytest.raises(ValidationError):
        _v(provenance_schema, bad)


def test_empty_evidence_fails(provenance_schema, valid_provenance):
    bad = copy.deepcopy(valid_provenance); bad["evidence"] = []
    with pytest.raises(ValidationError):
        _v(provenance_schema, bad)


def test_invalid_uncertainty_level_fails(provenance_schema, valid_provenance):
    bad = copy.deepcopy(valid_provenance); bad["uncertainty"]["level"] = "maybe"
    with pytest.raises(ValidationError):
        _v(provenance_schema, bad)


def test_invalid_algorithm_version_fails(provenance_schema, valid_provenance):
    bad = copy.deepcopy(valid_provenance); bad["algorithm_version"] = "v1"
    with pytest.raises(ValidationError):
        _v(provenance_schema, bad)
