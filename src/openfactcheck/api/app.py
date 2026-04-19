"""FastAPI application factory."""

from importlib.metadata import version

from fastapi import APIRouter, FastAPI

from openfactcheck.api.config import APIConfig
from openfactcheck.api.dependencies import get_config
from openfactcheck.api.middleware import register_middleware
from openfactcheck.api.routers import health, projects, workspaces


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = APIConfig()

    app = FastAPI(
        title="OpenFactCheck API",
        description=(
            "HTTP reference for the OpenFactCheck server.\n\n"
            "- **Interactive sandbox:** live Swagger UI at"
            " [`/docs`](https://api.openfactcheck.com/docs), ReDoc at"
            " [`/redoc`](https://api.openfactcheck.com/redoc).\n"
            "- **Auth:** every non-health endpoint expects an"
            " `Authorization: Bearer <token>` header.\n"
            "- **Errors:** failures return a structured JSON body with `detail`,"
            " `code`, and `status` fields."
        ),
        version=version("openfactcheck"),
        debug=config.debug,
    )

    # Override get_config so all dependencies see the same config instance.
    app.dependency_overrides[get_config] = lambda: config

    register_middleware(app, config.cors_origins)

    # Health — no version prefix (infrastructure).
    app.include_router(health.router)

    # v1 — all versioned API routes.
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(projects.router)
    v1.include_router(workspaces.router)
    app.include_router(v1)

    return app


app = create_app()
