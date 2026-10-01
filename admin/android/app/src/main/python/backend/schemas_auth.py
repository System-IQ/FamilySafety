"""Pydantic models for auth endpoints. Layer 1 (structural)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=5, max_length=254, pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class UserPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    email: str
    display_name: str
    created_at: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Full token pair returned by /login and /refresh (rotation)."""
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(min_length=10)
