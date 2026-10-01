"""Forgot-PIN flow — send + verify 6-digit email codes.

Two endpoints (both unauthenticated, rate-limited):
  POST /auth/forgot-pin   {email}                 -> sends code by email
  POST /auth/reset-pin    {email, code, new_pin}  -> verifies code

Design notes:
  - The PIN itself is NEVER sent to the server. It lives on the device.
  - The server only verifies ownership of the recovery email.
  - Codes are hashed (SHA-256) before storage — never stored in plaintext.
  - Codes expire after CODE_TTL_SECONDS (default 15 minutes).
  - Codes can be used only once.
  - Max MAX_ATTEMPTS verification attempts per code, then it's burned.
  - Rate limit: MAX_CODES_PER_WINDOW codes per email per window.
"""
import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status

from ..db import get_conn
from ..email_service import build_default_service
from ..schemas_password_reset import (
    ForgotPinRequest,
    ForgotPinResponse,
    ResetPinRequest,
    ResetPinResponse,
)

logger = logging.getLogger("familysafety.password_reset")
router = APIRouter(prefix="/auth", tags=["password-reset"])

# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────
CODE_TTL_SECONDS = int(os.getenv("FS_RESET_CODE_TTL", "900"))         # 15 min
MAX_ATTEMPTS = int(os.getenv("FS_RESET_MAX_ATTEMPTS", "5"))
RATE_WINDOW_SECONDS = int(os.getenv("FS_RESET_RATE_WINDOW", "900"))   # 15 min
MAX_CODES_PER_WINDOW = int(os.getenv("FS_RESET_MAX_CODES", "3"))
MIN_PIN_LENGTH = int(os.getenv("FS_PIN_MIN_LENGTH", "6"))
MAX_PIN_LENGTH = int(os.getenv("FS_PIN_MAX_LENGTH", "6"))
EXPOSE_RESET_CODE = os.getenv("FS_EXPOSE_RESET_CODE", "0") == "1"

# In-memory rate limiter: {email_lower: [timestamps]}
_rate_state: dict[str, list[float]] = {}

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _constant_time_eq_hex(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def _now_s() -> int:
    return int(time.time())


def _rate_check(email: str) -> None:
    key = email.strip().lower()
    now = time.time()
    stamps = _rate_state.get(key, [])
    stamps = [t for t in stamps if now - t < RATE_WINDOW_SECONDS]
    if len(stamps) >= MAX_CODES_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many reset requests — try again later",
        )
    stamps.append(now)
    _rate_state[key] = stamps


def _generate_code() -> str:
    """6-digit numeric code (000000..999999), cryptographically random."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _is_valid_email(s: str) -> bool:
    s = s.strip()
    if len(s) < 5 or len(s) > 254:
        return False
    if "@" not in s:
        return False
    local, _, domain = s.partition("@")
    if not local or not domain:
        return False
    if "." not in domain:
        return False
    return True


def _ensure_table() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_codes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT NOT NULL,
                code_hash   TEXT NOT NULL,
                expires_at  INTEGER NOT NULL,
                used        INTEGER NOT NULL DEFAULT 0,
                attempts    INTEGER NOT NULL DEFAULT 0,
                created_at  INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reset_email "
            "ON password_reset_codes(email)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reset_expires "
            "ON password_reset_codes(expires_at)"
        )


# ─────────────────────────────────────────────────────────────────────
# POST /auth/forgot-pin
# ─────────────────────────────────────────────────────────────────────

@router.post("/forgot-pin", response_model=ForgotPinResponse)
def forgot_pin(body: ForgotPinRequest, request: Request) -> ForgotPinResponse:
    email = (body.email or "").strip().lower()
    if not _is_valid_email(email):
        raise HTTPException(status_code=400, detail="invalid email")

    _rate_check(email)
    _ensure_table()

    # Invalidate previous un-used codes for this email
    now = _now_s()
    with get_conn() as conn:
        conn.execute(
            "UPDATE password_reset_codes SET used = 1 "
            "WHERE email = ? AND used = 0",
            (email,),
        )

    # Generate + store
    code = _generate_code()
    code_hash = _hash_code(code)
    expires_at = now + CODE_TTL_SECONDS

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO password_reset_codes
                (email, code_hash, expires_at, used, attempts, created_at)
            VALUES (?, ?, ?, 0, 0, ?)
            """,
            (email, code_hash, expires_at, now),
        )

    # Send email
    service = build_default_service()
    sent = False
    if service.enabled:
        sent = service.send_verification_code(
            to_email=email,
            code=code,
            ttl_minutes=CODE_TTL_SECONDS // 60,
        )
    else:
        logger.warning(
            "SMTP not configured — reset code for %s not sent "
            "(set FS_SMTP_USER + FS_SMTP_PASS)", email,
        )

    if not sent and not EXPOSE_RESET_CODE:
        raise HTTPException(
            status_code=503,
            detail="email service unavailable — contact your admin",
        )

    logger.info("forgot-pin: code issued for %s (sent=%s)", email, sent)

    return ForgotPinResponse(
        ok=True,
        message=(
            "A verification code was sent to your email. "
            "It expires in 15 minutes."
        ),
        dev_code=code if EXPOSE_RESET_CODE else None,
    )


# ─────────────────────────────────────────────────────────────────────
# POST /auth/reset-pin
# ─────────────────────────────────────────────────────────────────────

def _fetch_latest_reset_row(email: str):
    """Read-only transaction; returns a plain dict or None."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, code_hash, expires_at, used, attempts
            FROM password_reset_codes
            WHERE email = ?
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        ).fetchone()
    return dict(row) if row else None


def _bump_attempts(code_id: int) -> None:
    """Standalone write that survives raised HTTPException."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE password_reset_codes SET attempts = attempts + 1 "
            "WHERE id = ?",
            (code_id,),
        )


def _burn_code(code_id: int) -> None:
    """Standalone write that survives raised HTTPException."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE password_reset_codes SET used = 1 WHERE id = ?",
            (code_id,),
        )


@router.post("/reset-pin", response_model=ResetPinResponse)
def reset_pin(body: ResetPinRequest) -> ResetPinResponse:
    email = (body.email or "").strip().lower()
    code = (body.code or "").strip()
    new_pin = (body.new_pin or "").strip()

    if not _is_valid_email(email):
        raise HTTPException(status_code=400, detail="invalid email")

    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=400, detail="code must be 6 digits")

    if not new_pin.isdigit():
        raise HTTPException(
            status_code=400, detail="PIN must contain digits only",
        )
    if not (MIN_PIN_LENGTH <= len(new_pin) <= MAX_PIN_LENGTH):
        raise HTTPException(
            status_code=400,
            detail=f"PIN must be {MIN_PIN_LENGTH}–{MAX_PIN_LENGTH} digits",
        )

    _ensure_table()
    now = _now_s()

    # ─── Read phase (its own transaction) ───
    row = _fetch_latest_reset_row(email)

    if row is None:
        raise HTTPException(status_code=400, detail="no reset requested")

    if row["used"]:
        raise HTTPException(
            status_code=400, detail="code already used or expired",
        )

    if row["attempts"] >= MAX_ATTEMPTS:
        _burn_code(row["id"])
        raise HTTPException(
            status_code=400, detail="too many attempts — request a new code",
        )

    if now > row["expires_at"]:
        _burn_code(row["id"])
        raise HTTPException(status_code=400, detail="code expired")

    if not _constant_time_eq_hex(_hash_code(code), row["code_hash"]):
        _bump_attempts(row["id"])
        raise HTTPException(status_code=400, detail="invalid code")

    # ─── Success — burn code in its own transaction ───
    _burn_code(row["id"])

    logger.info("reset-pin: code verified for %s", email)

    return ResetPinResponse(
        ok=True,
        message="Code verified. You may now set your new PIN on the device.",
    )
