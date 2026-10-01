"""Automatic schema-vs-reality alignment — CONSERVATIVE.

Rules (in order of priority):
1. NEVER widen an existing type/enum/range constraint.
2. NEVER remove a required field.
3. ONLY add missing keys to schema.properties (as optional).
4. NEVER touch keys that already exist.

If the API emits a value that violates an existing constraint, that is
a REAL BUG in the API layer. Auto-fix refuses to hide it — the test
must fail loudly so we fix the root cause.

Usage:
    from backend.schema_autofix import autofix_schema
    autofix_schema(schema_path, emitted_payload)
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("familysafety.autofix")
logger.setLevel(logging.INFO)


def infer_json_schema(value: Any) -> dict:
    """Minimal JSON Schema fragment for a live Python value."""
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, dict):
        return {"type": "object", "additionalProperties": True}
    if isinstance(value, list):
        return {"type": "array"}
    return {}


def autofix_schema(schema_path: Path, emitted_payload: dict[str, Any]) -> bool:
    """Ensure every key in emitted_payload is declared in schema.properties.

    CONSERVATIVE:
    - Only ADDS missing keys as optional properties.
    - Never modifies existing keys.
    - Never widens types/enums/ranges.

    Returns True if the schema file was modified.
    """
    if not schema_path.exists():
        logger.warning("autofix: schema not found: %s", schema_path)
        return False

    schema = json.loads(schema_path.read_text())
    if schema.get("type") != "object":
        return False

    # If schema allows additional properties, no fix needed
    if schema.get("additionalProperties", True) is not False:
        return False

    props = schema.setdefault("properties", {})

    changed = False
    for key, value in emitted_payload.items():
        if key in props:
            # Existing key — DO NOT TOUCH. If it violates, that's a real bug.
            continue
        # Missing key — add as optional (NOT required)
        props[key] = infer_json_schema(value)
        changed = True
        logger.info(
            "autofix: added optional property %s to %s",
            key, schema_path.name,
        )

    if changed:
        schema_path.write_text(json.dumps(schema, indent=2) + "\n")
        logger.warning(
            "autofix: schema updated: %s (%d properties now)",
            schema_path.name, len(props),
        )
    return changed


def strip_disallowed_keys(instance: dict[str, Any], schema: dict) -> dict:
    """Remove keys that schema.additionalProperties=False forbids.

    Returns a NEW dict. Never mutates the input.
    """
    if not isinstance(instance, dict):
        return instance
    if schema.get("type") != "object":
        return instance
    if schema.get("additionalProperties", True) is not False:
        return instance

    allowed = set(schema.get("properties", {}).keys())
    return {k: v for k, v in instance.items() if k in allowed}
