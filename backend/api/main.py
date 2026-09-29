"""FastAPI application factory."""
from fastapi import FastAPI

from ..db import init_db
from ..observability import RequestLogMiddleware
from .alerts import router as alerts_router
from .algorithms import router as algorithms_router
from .audit import router as audit_router
from .auth import router as auth_router
from .derived import router as derived_router
from .devices import router as devices_router
from .events import router as events_router
from .health import router as health_router
from .zones import router as zones_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Family Safety API",
        version="0.7.0",
        description="Backend for Family Safety A/B.",
    )
    app.add_middleware(RequestLogMiddleware)
    init_db()
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(devices_router)
    app.include_router(events_router)
    app.include_router(audit_router)
    app.include_router(zones_router)
    app.include_router(alerts_router)
    app.include_router(algorithms_router)
    app.include_router(derived_router)
    return app


app = create_app()
