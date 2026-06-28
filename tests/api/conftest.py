"""API integration test fixtures — test client, mock auth, in-memory SQLite."""

import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from openfactcheck.api.app import create_app
from openfactcheck.api.auth.dev import DEV_USER
from openfactcheck.api.config import APIConfig
from openfactcheck.api.crypto.local import LocalCipher
from openfactcheck.api.dependencies import (
    get_cipher,
    get_current_user,
    get_preferences_repo,
    get_project_repo,
    get_secret_repo,
    get_workspace_repo,
)
from openfactcheck.api.models import AuthUser
from openfactcheck.api.repositories.sqlite.engine import create_engine, create_session_factory, create_tables
from openfactcheck.api.repositories.sqlite.preferences import SqlitePreferencesRepository
from openfactcheck.api.repositories.sqlite.projects import SqliteProjectRepository
from openfactcheck.api.repositories.sqlite.secrets import SqliteSecretRepository
from openfactcheck.api.repositories.sqlite.workspaces import SqliteWorkspaceRepository

TEST_USER = DEV_USER


@pytest_asyncio.fixture(loop_scope="function")
async def client() -> AsyncIterator[AsyncClient]:
    """Yield an httpx AsyncClient wired to a test app with in-memory SQLite and mock auth."""
    engine = create_engine(":memory:")
    await create_tables(engine)
    sf = create_session_factory(engine)
    project_repo = SqliteProjectRepository(sf)
    workspace_repo = SqliteWorkspaceRepository(sf)
    secret_repo = SqliteSecretRepository(sf)
    preferences_repo = SqlitePreferencesRepository(sf)

    key_dir = tempfile.mkdtemp()
    cipher = LocalCipher(str(Path(key_dir) / "secrets.key"))

    config = APIConfig(auth_bypass=True)
    app = create_app(config)

    async def override_current_user() -> AuthUser:
        return TEST_USER

    async def override_project_repo() -> SqliteProjectRepository:
        return project_repo

    async def override_workspace_repo() -> SqliteWorkspaceRepository:
        return workspace_repo

    async def override_secret_repo() -> SqliteSecretRepository:
        return secret_repo

    async def override_preferences_repo() -> SqlitePreferencesRepository:
        return preferences_repo

    async def override_cipher() -> LocalCipher:
        return cipher

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_project_repo] = override_project_repo
    app.dependency_overrides[get_workspace_repo] = override_workspace_repo
    app.dependency_overrides[get_secret_repo] = override_secret_repo
    app.dependency_overrides[get_preferences_repo] = override_preferences_repo
    app.dependency_overrides[get_cipher] = override_cipher

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    await engine.dispose()
    shutil.rmtree(key_dir, ignore_errors=True)
