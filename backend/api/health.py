"""Real health endpoint — checks actual DB connectivity."""
import sqlite3
import time

from fastapi import APIRouter

from ..config import settings

router = APIRouter(tags=["health"])
_STARTED_AT = time.time()


@router.get("/health")
def health() -> dict:
    db_ok = False
    db_error: str | None = None
    try:
        with sqlite3.connect(settings.db_path) as conn:
            conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception as exc:
        db_error = str(exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - _STARTED_AT, 3),
        "checks": {
            "database": {"ok": db_ok, "error": db_error},
        },
    }
