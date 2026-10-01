"""Pydantic models — Layer 1 (structural validation)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Battery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level_percent: int = Field(ge=0, le=100)
    charging: bool
    timestamp: datetime


class LocationCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: bool
    permission_state: Literal["granted", "denied", "restricted", "not_determined"]
    background_supported: bool


class DeviceIn(BaseModel):
    """Matches shared/contracts/v1/device.schema.json."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=4)
    device_name: str = Field(min_length=1)
    platform: Literal["android", "ios"]
    android_version: str
    app_version: str
    management_state: Literal["unmanaged", "managed", "device_owner", "unsupported"]
    connection_state: Literal["online", "weak", "intermittent", "offline"]
    battery: Battery
    last_seen: datetime
    location_capability: LocationCapability
    created_at: datetime
    updated_at: datetime
