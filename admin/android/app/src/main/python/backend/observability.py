"""Request metadata helper + structured logging middleware.

Middleware logs every request as a single JSON line to stdout
AND records it in the system_metrics request counter.
This is observability — NOT audit. Audit is business-level and lives
in backend.audit_repo (explicit calls in endpoints).
"""
import json
import logging
import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from . import system_metrics

logger = logging.getLogger("familysafety.http")
logger.setLevel(logging.INFO)


def request_meta(request: Request) -> dict[str, Any]:
    """Return ip_address + user_agent for use in audit records."""
    ip: str | None = None
    if request.client is not None:
        ip = request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent"),
    }


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Log each request as one JSON line. Record into metrics counter."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(json.dumps({
                "method": request.method,
                "path": request.url.path,
                "status": status_code,
                "duration_ms": duration_ms,
            }))
            try:
                system_metrics.record_request(status_code)
            except Exception:
                pass
