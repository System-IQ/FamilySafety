"""Pydantic schemas for the Forgot-PIN flow.

Uses _BaseModel so it works on both:
  - Android (pydantic v1.10.15, Chaquopy)
  - Dev/CI (pydantic v2.x)
"""
from typing import Optional

from ._base_model import BaseModel


class ForgotPinRequest(BaseModel):
    email: str


class ForgotPinResponse(BaseModel):
    ok: bool
    message: str
    # Never echo the code back. Only used in tests where explicitly
    # enabled via FS_EXPOSE_RESET_CODE=1.
    dev_code: Optional[str] = None


class ResetPinRequest(BaseModel):
    email: str
    code: str
    new_pin: str


class ResetPinResponse(BaseModel):
    ok: bool
    message: str
