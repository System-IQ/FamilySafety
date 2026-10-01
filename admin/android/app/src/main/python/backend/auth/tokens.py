"""JWT creation/verification. HS256 only. Pure Python (pyjwt).

Access token  : short-lived (minutes), no server state.
Refresh token : long-lived (days), has jti, stored hashed in DB,
                MUST be rotated on every use (revoke old + issue new).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


class TokenError(Exception):
    """Any token validation failure."""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: str, secret: str, minutes: int = 15
) -> tuple[str, datetime]:
    """Return (token, expires_at_utc)."""
    now = _now_utc()
    expires_at = now + timedelta(minutes=minutes)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm="HS256"), expires_at


def create_refresh_token(
    user_id: str, secret: str, days: int = 30
) -> tuple[str, str, datetime]:
    """Return (jti, token, expires_at_utc)."""
    now = _now_utc()
    expires_at = now + timedelta(days=days)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "refresh",
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return jti, token, expires_at


def decode_token(
    token: str, secret: str, expected_type: str | None = None
) -> dict[str, Any]:
    """Verify signature + expiry + (optionally) token type."""
    if not isinstance(token, str) or token.count(".") != 2:
        raise TokenError("malformed token")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"invalid token: {exc}") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise TokenError(
            f"expected {expected_type} token, got {payload.get('type')!r}"
        )
    return payload
