"""Build info — useful for verifying which commit is deployed."""
import os
import platform
import sys
import time

from fastapi import APIRouter

from ..db import db_backend
from ..config import settings

router = APIRouter(tags=["version"])

_STARTED_AT = time.time()

# Render sets RENDER_GIT_COMMIT for every deploy
_COMMIT = os.getenv("RENDER_GIT_COMMIT", "dev")[:12]
_BRANCH = os.getenv("RENDER_GIT_BRANCH", "local")
_SERVICE = os.getenv("RENDER_SERVICE_NAME", "familysafety-api-local")


@router.get("/version")
def version() -> dict:
    return {
        "service": _SERVICE,
        "commit": _COMMIT,
        "branch": _BRANCH,
        "environment": settings.environment,
        "database_backend": db_backend(),
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.machine()}",
        "uptime_seconds": round(time.time() - _STARTED_AT, 3),
    }
