"""Pydantic models for /audit endpoints (read-only)."""
from typing import Any, Optional

from pydantic import BaseModel, Field
from ._base_model import BaseModel as _BaseModel


class AuditOut(_BaseModel):
    audit_id: str
    actor_user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    result: str
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditListResponse(_BaseModel):
    audit: list[AuditOut]
