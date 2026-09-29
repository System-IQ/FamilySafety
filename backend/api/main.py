"""FastAPI application factory."""
from fastapi import FastAPI

from ..db import init_db
from .devices import router as devices_router
from .health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Family Safety API",
        version="0.1.0",
        description="Backend for Family Safety A/B.",
    )
    init_db()
    app.include_router(health_router)
    app.include_router(devices_router)
    return app


app = create_app()
