"""Deep health check — DB ping + latency + backend type.

Backward compatible with the original shape:
    {"status", "environment", "uptime_seconds",
     "checks": {"database": {"ok": bool, "error": str|null}}}

Also enriched with:
    checks.database.backend     "sqlite" | "postgresql"
    checks.database.latency_ms  float

Returns 200 when healthy, 503 when DB is unreachable.
Works with Render's healthCheckPath.
"""
import time

from fastapi import APIRouter, Response, status

from ..config import settings
from ..db import db_backend, ping

router = APIRouter(tags=["health"])
_STARTED_AT = time.time()


@router.get("/health")
def health(response: Response) -> dict:
    ok, err, latency_ms = ping()

    body = {
        "status": "ok" if ok else "degraded",
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - _STARTED_AT, 3),
        "checks": {
            "database": {
                "ok": ok,
                "error": err,
                "backend": db_backend(),
                "latency_ms": latency_ms,
            }
        },
    }

    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return body
