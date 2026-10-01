"""Pydantic models for auth endpoints. Layer 1 (structural)."""
from typing import Literal

from pydantic import BaseModel, Field
from ._base_model import BaseModel as _BaseModel

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(_BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class UserPublic(_BaseModel):
    user_id: str
    email: str
    display_name: str
    created_at: str


class LoginRequest(_BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(_BaseModel):
    """Full token pair returned by /login and /refresh (rotation)."""
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class RefreshRequest(_BaseModel):
    refresh_token: str = Field(min_length=10)
