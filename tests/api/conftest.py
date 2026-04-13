"""API integration test fixtures — test client, mock auth, in-memory SQLite."""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from openfactcheck.api.app import create_app
from openfactcheck.api.auth.cognito import DEV_USER
from openfactcheck.api.config import APIConfig
from openfactcheck.api.dependencies import get_current_user, get_project_repo, get_workspace_repo
from openfactcheck.api.models import AuthUser
from openfactcheck.api.repositories.sqlite.engine import create_engine_and_tables, session_factory
from openfactcheck.api.repositories.sqlite.projects import SqliteProjectRepository
from openfactcheck.api.repositories.sqlite.workspaces import SqliteWorkspaceRepository

TEST_USER = DEV_USER


@pytest_asyncio.fixture(loop_scope="function")
async def client() -> AsyncIterator[AsyncClient]:
    """Yield an httpx AsyncClient wired to a test app with in-memory SQLite and mock auth."""
    engine = await create_engine_and_tables(":memory:")
    sf = session_factory(engine)
    project_repo = SqliteProjectRepository(sf)
    workspace_repo = SqliteWorkspaceRepository(sf)

    config = APIConfig(auth_bypass=True)
    app = create_app(config)

    async def override_current_user() -> AuthUser:
        return TEST_USER

    async def override_project_repo() -> SqliteProjectRepository:
        return project_repo

    async def override_workspace_repo() -> SqliteWorkspaceRepository:
        return workspace_repo

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_project_repo] = override_project_repo
    app.dependency_overrides[get_workspace_repo] = override_workspace_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    await engine.dispose()
