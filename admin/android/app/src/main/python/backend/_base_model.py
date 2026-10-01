"""Pydantic v1/v2 compatibility shim.

Why: Chaquopy (Android) cannot build pydantic-core (Rust), so the app
runs with pydantic v1 + fastapi 0.99. Dev + CI use pydantic v2. This
module exports a BaseModel that behaves identically in both worlds.
"""
import pydantic


def _version_major() -> int:
    try:
        return int(pydantic.VERSION.split(".")[0])
    except Exception:
        return 2


PYDANTIC_V2 = _version_major() >= 2


if PYDANTIC_V2:
    from pydantic import BaseModel as _BasePydantic

    class BaseModel(_BasePydantic):  # type: ignore[misc, valid-type]
        """pydantic v2 BaseModel with extra='forbid'."""
        model_config = pydantic.ConfigDict(extra="forbid")
else:
    from pydantic import BaseModel as _BasePydantic

    class BaseModel(_BasePydantic):  # type: ignore[misc, valid-type]
        """pydantic v1 BaseModel with extra='forbid'."""

        class Config:
            extra = "forbid"


def dump_json(model) -> dict:
    """JSON-safe dict from a pydantic model (v1 or v2)."""
    if PYDANTIC_V2:
        return model.model_dump(mode="json")
    import json
    return json.loads(model.json())


def parse_obj(cls, data):
    """Parse a dict into a pydantic model (v1 or v2)."""
    if PYDANTIC_V2:
        return cls.model_validate(data)
    return cls.parse_obj(data)


def model_dump(model) -> dict:
    """Plain dict from a pydantic model (v1 or v2)."""
    if PYDANTIC_V2:
        return model.model_dump()
    return model.dict()
