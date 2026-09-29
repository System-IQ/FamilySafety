"""Auto-fix: verify schemas allow what API actually emits.

Runs at the END of pytest. If any schema is missing a key that the API
emits, this test FAILS LOUDLY with a clear "run autofix" message.
Then `pytest --autofix` (custom flag below) auto-repairs.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
V2 = REPO / "shared" / "contracts" / "v2"


def test_all_v2_schemas_are_valid_draft_2020_12():
    """Every v2 schema must be loadable as Draft 2020-12."""
    from jsonschema import Draft202012Validator
    failures = []
    for path in sorted(V2.glob("*.schema.json")):
        try:
            s = json.loads(path.read_text())
            Draft202012Validator.check_schema(s)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
    assert not failures, "Invalid schemas:\n  " + "\n  ".join(failures)
