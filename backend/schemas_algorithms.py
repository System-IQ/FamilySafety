"""Pydantic models for /algorithms endpoints."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TestStatus = Literal["unknown", "partial", "passing", "failing"]
PromoteTarget = Literal["testing", "canary", "production", "blocked", "deprecated"]

_ALGO_ID_PATTERN = r"^[a-z][a-z0-9_]{2,63}$"
_SEMVER_PATTERN = r"^[0-9]+\.[0-9]+\.[0-9]+$"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    algorithm_id: str = Field(min_length=3, max_length=64, pattern=_ALGO_ID_PATTERN)
    version: str = Field(min_length=5, max_length=20, pattern=_SEMVER_PATTERN)
    name: str = Field(min_length=3, max_length=128)
    description: Optional[str] = Field(default=None, max_length=1024)
    input_schema_ref: str = Field(min_length=3, max_length=128)
    output_schema_ref: str = Field(min_length=3, max_length=128)
    test_status: TestStatus = "unknown"


class AlgorithmOut(BaseModel):
    algorithm_id: str
    version: str
    name: str
    description: Optional[str] = None
    input_schema_ref: str
    output_schema_ref: str
    status: str
    test_status: str
    created_at: str
    updated_at: Optional[str] = None
    deprecated_at: Optional[str] = None
    deprecation_reason: Optional[str] = None
    superseded_by: Optional[str] = None


class AlgorithmListResponse(BaseModel):
    algorithms: list[AlgorithmOut]


class SetTestStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_status: TestStatus


class PromoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: PromoteTarget
    reason: Optional[str] = Field(default=None, max_length=512)
    superseded_by: Optional[str] = Field(default=None, max_length=64)
