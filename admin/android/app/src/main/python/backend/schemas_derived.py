"""Pydantic models for /derived endpoints."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from ._base_model import BaseModel as _BaseModel

RecordType = Literal[
    "cleaned_location",
    "route_summary",
    "stop_detection",
    "speed_anomaly",
    "geofence_state",
    "data_quality_report",
]

UncertaintyLevel = Literal["none", "low", "medium", "high"]

_ALGO_ID_PATTERN = r"^[a-z][a-z0-9_]{2,63}$"
_SEMVER_PATTERN = r"^[0-9]+\.[0-9]+\.[0-9]+$"


class Uncertainty(_BaseModel):
    level: UncertaintyLevel = "none"
    notes: Optional[str] = Field(default=None, max_length=1024)


class ProvenanceIn(_BaseModel):
    source_record_ids: list[str] = Field(min_length=1)
    algorithm_id: str = Field(min_length=3, max_length=64, pattern=_ALGO_ID_PATTERN)
    algorithm_version: str = Field(min_length=5, max_length=20, pattern=_SEMVER_PATTERN)
    calculated_at: Optional[str] = Field(default=None, min_length=20, max_length=30)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(min_length=1)
    uncertainty: Optional[Uncertainty] = None
    input_hash: Optional[str] = Field(default=None, min_length=32)


class DerivedCreate(_BaseModel):
    device_id: str = Field(min_length=4, max_length=128)
    record_type: RecordType
    timestamp: str = Field(min_length=20, max_length=30)
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceIn
    quality_score: float = Field(ge=0.0, le=100.0)
    insufficient_data: bool = False
    insufficient_reason: Optional[str] = Field(default=None, max_length=512)


class DerivedOut(_BaseModel):
    record_id: str
    device_id: str
    record_type: str
    timestamp: str
    payload: dict[str, Any]
    provenance: dict[str, Any]
    quality_score: float
    insufficient_data: bool
    insufficient_reason: Optional[str] = None
    created_at: str


class DerivedListResponse(_BaseModel):
    records: list[DerivedOut]
