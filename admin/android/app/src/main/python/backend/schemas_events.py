"""Pydantic models for /events endpoints. Layer 1 validation."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["info", "warning", "critical"]

EventType = Literal[
    "device_online",
    "device_offline",
    "connection_degraded",
    "location_update",
    "location_stale",
    "sync_started",
    "sync_completed",
    "sync_failed",
    "safe_zone_enter",
    "safe_zone_exit",
    "sos_triggered",
    "sos_acknowledged",
    "battery_low",
    "battery_critical",
    "permission_changed",
    "command_issued",
    "command_completed",
    "command_failed",
    "algorithm_published",
    "algorithm_rolled_back",
]


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=4, max_length=128)
    event_type: EventType
    severity: Severity
    timestamp: str = Field(min_length=20, max_length=30)
    payload: Optional[dict[str, Any]] = None
    correlation_id: Optional[str] = Field(default=None, min_length=4, max_length=128)


class EventOut(BaseModel):
    event_id: str
    device_id: str
    event_type: str
    severity: str
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None


class EventListResponse(BaseModel):
    events: list[EventOut]
