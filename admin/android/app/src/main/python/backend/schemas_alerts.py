"""Pydantic models for /alerts endpoints."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AlertType = Literal[
    "sos",
    "low_battery",
    "critical_battery",
    "device_offline",
    "geofence_exit",
    "geofence_enter",
    "speed_exceeded",
    "route_anomaly",
    "unexpected_stop",
    "permission_revoked",
    "gps_unavailable",
]

Severity = Literal["info", "warning", "critical"]

AlertState = Literal["new", "acknowledged", "resolved", "dismissed", "expired"]


class LastLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: Optional[float] = Field(default=None, ge=0)
    timestamp: str = Field(min_length=20, max_length=30)


class AlertCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=4, max_length=128)
    alert_type: AlertType
    severity: Severity
    triggered_at: Optional[str] = Field(default=None, min_length=20, max_length=30)
    note: Optional[str] = Field(default=None, max_length=512)
    last_location: Optional[LastLocation] = None
    battery_level_percent: Optional[int] = Field(default=None, ge=0, le=100)


class AlertOut(BaseModel):
    alert_id: str
    device_id: str
    alert_type: str
    severity: str
    state: str
    triggered_at: str
    note: Optional[str] = None
    last_location: Optional[dict[str, Any]] = None
    battery_level_percent: Optional[int] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    dismissed_at: Optional[str] = None
    dismiss_reason: Optional[str] = None
    created_at: str
    updated_at: str


class AlertListResponse(BaseModel):
    alerts: list[AlertOut]


class AcknowledgeRequest(BaseModel):
    """No body needed — kept for future extension."""


class ResolveRequest(BaseModel):
    """No body needed — kept for future extension."""


class DismissRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Optional[str] = Field(default=None, max_length=512)
