"""Layer 2: JSON Schema contract validation.

Schemas are looked up in v2 first, then v1.
This lets new contracts (event, alert, safe_zone, ...) live in v2
without changing callers, while existing v1 contracts keep working.
"""
import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .config import settings

_FORMAT_CHECKER = FormatChecker()


def _candidate_paths(schema_filename: str):
    # v2 first (newer wins if duplicate names ever appear)
    return (
        settings.contracts_v2_dir / schema_filename,
        settings.contracts_v1_dir / schema_filename,
    )


@lru_cache(maxsize=64)
def _validator_for(schema_filename: str) -> Draft202012Validator:
    for path in _candidate_paths(schema_filename):
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                schema = json.load(f)
            return Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)
    searched = "\n  ".join(str(p) for p in _candidate_paths(schema_filename))
    raise FileNotFoundError(
        f"Contract schema '{schema_filename}' not found. Searched:\n  {searched}"
    )


def validate_contract(schema_filename: str, instance: dict[str, Any]) -> None:
    """Validate instance against a named contract schema.

    Raises jsonschema.ValidationError on failure,
    FileNotFoundError if the schema is missing in v1 and v2.
    """
    _validator_for(schema_filename).validate(instance)
