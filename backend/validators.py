"""Layer 2: JSON Schema contract validation (source of truth)."""
import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .config import settings

_FORMAT_CHECKER = FormatChecker()


@lru_cache(maxsize=32)
def _validator_for(schema_filename: str) -> Draft202012Validator:
    path = settings.contracts_dir / schema_filename
    if not path.exists():
        raise FileNotFoundError(f"Contract schema not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    return Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)


def validate_contract(schema_filename: str, instance: dict[str, Any]) -> None:
    """Validate instance against a named contract schema.

    Raises jsonschema.ValidationError on failure.
    """
    _validator_for(schema_filename).validate(instance)
