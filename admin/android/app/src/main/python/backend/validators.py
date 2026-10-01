"""Layer 2: JSON Schema contract validation.

If `jsonschema` is not available (e.g. embedded Chaquopy runtime on
Android where rpds-py cannot be built), contract validation is
skipped. The Pydantic layer (Layer 1) still validates every request.
"""
import json
import logging
from functools import lru_cache
from typing import Any

from .config import settings

logger = logging.getLogger("familysafety.validators")

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema import ValidationError as JsonSchemaError
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False
    logger.warning(
        "jsonschema not available — contract validation disabled "
        "(Pydantic layer still active)"
    )

    class JsonSchemaError(Exception):  # type: ignore[no-redef]
        """Fallback when jsonschema is missing."""
        def __init__(self, message: str = "", *args, **kwargs):
            super().__init__(message)
            self.message = message
            self.absolute_path: list = []


def _candidate_paths(schema_filename: str):
    return (
        settings.contracts_v2_dir / schema_filename,
        settings.contracts_v1_dir / schema_filename,
    )


@lru_cache(maxsize=64)
def _validator_for(schema_filename: str):
    if not _HAS_JSONSCHEMA:
        return None
    for path in _candidate_paths(schema_filename):
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                schema = json.load(f)
            return Draft202012Validator(schema, format_checker=FormatChecker())
    searched = "\n  ".join(str(p) for p in _candidate_paths(schema_filename))
    raise FileNotFoundError(
        f"Contract schema '{schema_filename}' not found. Searched:\n  {searched}"
    )


def validate_contract(schema_filename: str, instance: dict[str, Any]) -> None:
    """Validate instance against a named contract schema.

    No-op when jsonschema is unavailable (embedded runtime).
    Raises JsonSchemaError on failure (when available).
    """
    if not _HAS_JSONSCHEMA:
        return
    validator = _validator_for(schema_filename)
    if validator is not None:
        validator.validate(instance)
