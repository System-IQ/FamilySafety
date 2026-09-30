"""/metrics — live system metrics for the Server Dashboard.

Public (no auth required) so the dashboard can refresh without login.
Returns CPU, memory, battery, storage, network, database, requests.
"""
from fastapi import APIRouter

from .. import system_metrics
from ..config import settings

router = APIRouter(tags=["system"])


@router.get("/metrics")
def get_metrics() -> dict:
    """Return a live snapshot of the server's system state."""
    db_path = str(settings.db_path)
    return system_metrics.collect(db_path=db_path)
