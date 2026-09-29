"""Refresh token persistence (hashed at rest).

Rotation is the default: every /refresh call revokes the old
token and stores a new one — atomically.
"""
from datetime import datetime, timezone
from typing import Optional

from ..db import get_conn


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def store_refresh_token(
    token_id: str,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO refresh_tokens
                (token_id, user_id, token_hash, expires_at,
                 created_at, revoked)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (token_id, user_id, token_hash, _iso(expires_at), _utcnow_iso()),
        )


def get_refresh_token(token_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT token_id, user_id, token_hash, expires_at, created_at, revoked
            FROM refresh_tokens WHERE token_id = ?
            """,
            (token_id,),
        ).fetchone()
    return dict(row) if row else None


def revoke_refresh_token(token_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE token_id = ?",
            (token_id,),
        )


def consume_and_rotate(
    old_jti: str,
    new_jti: str,
    user_id: str,
    new_token_hash: str,
    new_expires_at: datetime,
) -> bool:
    """Atomically consume old refresh token and store a new one.

    The UPDATE is conditional on revoked=0. If rowcount != 1,
    it means the old token was already consumed (or never existed)
    — a replay attempt or a race. Returns False without inserting.

    Returns True on success. The whole operation runs in a single
    transaction: either both the revoke and the insert succeed,
    or neither does.
    """
    with get_conn() as conn:
        cur = conn.execute(
            """
            UPDATE refresh_tokens
            SET revoked = 1
            WHERE token_id = ? AND revoked = 0
            """,
            (old_jti,),
        )
        if cur.rowcount != 1:
            return False

        conn.execute(
            """
            INSERT INTO refresh_tokens
                (token_id, user_id, token_hash, expires_at,
                 created_at, revoked)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                new_jti,
                user_id,
                new_token_hash,
                _iso(new_expires_at),
                _utcnow_iso(),
            ),
        )
        return True
