"""Pydantic models for /zones endpoints."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from ._base_model import BaseModel as _BaseModel

_Day = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_HHMM_PATTERN = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"


class Center(_BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Schedule(_BaseModel):
    days: list[_Day] = Field(min_length=1)
    start_time: str = Field(pattern=_HHMM_PATTERN)
    end_time: str = Field(pattern=_HHMM_PATTERN)


class ZoneCreate(_BaseModel):
    device_id: str = Field(min_length=4, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    center: Center
    radius_meters: float = Field(ge=10, le=50000)
    enabled: bool = True
    schedule: Optional[Schedule] = None


class ZoneUpdate(_BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    center: Optional[Center] = None
    radius_meters: Optional[float] = Field(default=None, ge=10, le=50000)
    enabled: Optional[bool] = None
    schedule: Optional[Schedule] = None
    clear_schedule: bool = False


class ZoneOut(_BaseModel):
    zone_id: str
    device_id: str
    name: str
    center: Center
    radius_meters: float
    enabled: bool
    schedule: Optional[Schedule] = None
    created_at: str
    updated_at: Optional[str] = None


class ZoneListResponse(_BaseModel):
    zones: list[ZoneOut]


class EvaluateRequest(_BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    at_utc: Optional[str] = None   # ISO8601 Z; if None -> now


class EvaluateResponse(_BaseModel):
    zone_id: str
    device_id: str
    distance_meters: float
    within_radius: bool
    within_schedule: bool
    inside: bool
    entered: bool
    exited: bool
    enabled: bool
    was_inside: bool
    evaluated_at: str
    event_id: Optional[str] = None  # if an event was emitted
