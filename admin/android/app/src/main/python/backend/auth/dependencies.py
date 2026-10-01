"""FastAPI dependencies for authenticated routes.

Two modes:
  1. Access-code mode (Android / single-user)
       FS_ACCESS_CODE is set → any Bearer matching it is accepted
       and mapped to a synthetic local user.
  2. JWT mode (server / multi-user)
       FS_ACCESS_CODE empty → normal JWT access token required.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings
from . import users_repo
from .tokens import TokenError, decode_token

_bearer = HTTPBearer(auto_error=False)


_LOCAL_USER = {
    "user_id": "local_admin",
    "email": "local@device",
    "display_name": "Local Admin",
    "created_at": "",
    "updated_at": "",
    "is_active": True,
}


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials

    # ── Mode 1: access-code ──
    if settings.access_code:
        if token == settings.access_code:
            return dict(_LOCAL_USER)
        # Fall through to JWT in case an admin uses a real JWT

    # ── Mode 2: JWT ──
    try:
        payload = decode_token(token, settings.jwt_secret, expected_type="access")
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = users_repo.get_by_id(payload["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not found",
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user disabled",
        )
    return user
