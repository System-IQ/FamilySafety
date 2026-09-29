"""User persistence. SQLite. Real DB — no mocks."""
from datetime import datetime, timezone
from typing import Optional

from ..db import get_conn


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_user(
    user_id: str,
    email: str,
    display_name: str,
    password_hash: str,
) -> dict:
    """Insert a new user. Email is stored lowercased."""
    now = _utcnow_iso()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users
                (user_id, email, display_name, password_hash,
                 created_at, updated_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, email.lower(), display_name, password_hash, now, now),
        )
    return {
        "user_id": user_id,
        "email": email.lower(),
        "display_name": display_name,
        "created_at": now,
        "updated_at": now,
        "is_active": True,
    }


def get_by_email(email: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT user_id, email, display_name, password_hash,
                   created_at, updated_at, is_active
            FROM users WHERE email = ?
            """,
            (email.lower(),),
        ).fetchone()
    return dict(row) if row else None


def get_by_id(user_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT user_id, email, display_name, password_hash,
                   created_at, updated_at, is_active
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None
