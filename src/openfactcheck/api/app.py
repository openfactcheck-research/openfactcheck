"""FastAPI application factory."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from openfactcheck.api.config import APIConfig
from openfactcheck.api.dependencies import get_config
from openfactcheck.api.middleware import register_middleware
from openfactcheck.api.routers import health, projects, runs, workspaces


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = APIConfig()

    app = FastAPI(
        title="OpenFactCheck API",
        description="API for executing fact-checking pipelines",
        debug=config.debug,
    )

    # Override get_config so all dependencies see the same config instance
    app.dependency_overrides[get_config] = lambda: config

    register_middleware(app, config.cors_origins)

    # Health — no version prefix (infrastructure)
    app.include_router(health.router)

    # v1 — all versioned API routes
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(projects.router)
    v1.include_router(workspaces.router)
    v1.include_router(runs.router)
    app.include_router(v1)

    return app


app = create_app()
