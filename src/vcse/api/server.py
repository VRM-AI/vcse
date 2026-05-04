"""FastAPI server assembly."""

from __future__ import annotations

from fastapi import FastAPI

from vcse.api.config import API_VERSION
from vcse.api.middleware import install_error_handlers
from vcse.api.routes import router
from vcse.api.routes_health import router as health_router
from vcse.api.routes_pack import router as pack_router
from vcse.api.routes_query import router as query_router
from vcse.api.routes_reason import router as reason_router
from vcse.api.routes_runtime import router as runtime_router
from vcse.config import load_settings, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title="VCSE API Adapter", version=API_VERSION)
    app.state.settings = runtime_settings
    app.include_router(router)
    app.include_router(health_router)
    app.include_router(runtime_router)
    app.include_router(pack_router)
    app.include_router(query_router)
    app.include_router(reason_router)
    install_error_handlers(
        app,
        max_request_bytes=runtime_settings.api_max_request_bytes,
        timeout_seconds=runtime_settings.api_timeout_seconds,
    )
    return app
