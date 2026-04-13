"""FastAPI dependency injection — settings, auth, repositories."""

import asyncio
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, Header

from openfactcheck.api.auth.cognito import CognitoVerifier, DevVerifier, TokenVerifier
from openfactcheck.api.config import APIConfig
from openfactcheck.api.errors import AuthError
from openfactcheck.api.models import AuthUser
from openfactcheck.api.repositories.protocols import ProjectRepository, WorkspaceRepository


@lru_cache(maxsize=1)
def get_config() -> APIConfig:
    """Return the singleton API configuration."""
    return APIConfig()


_verifier: TokenVerifier | None = None
_project_repo: ProjectRepository | None = None
_workspace_repo: WorkspaceRepository | None = None
_sqlite_session_factory: Any = None
_sqlite_lock = asyncio.Lock()


async def _get_sqlite_session_factory(config: APIConfig) -> Any:  # noqa: ANN401
    """Return a shared SQLite session factory, creating the engine once (thread-safe)."""
    global _sqlite_session_factory  # noqa: PLW0603
    if _sqlite_session_factory is not None:
        return _sqlite_session_factory
    async with _sqlite_lock:
        if _sqlite_session_factory is None:
            from openfactcheck.api.repositories.sqlite.engine import create_engine_and_tables, session_factory

            engine = await create_engine_and_tables(config.sqlite_path)
            _sqlite_session_factory = session_factory(engine)
    return _sqlite_session_factory


async def get_verifier(config: Annotated[APIConfig, Depends(get_config)]) -> TokenVerifier:
    """Return the token verifier, creating it on first call."""
    global _verifier  # noqa: PLW0603
    if _verifier is None:
        if config.auth_bypass and config.debug:
            _verifier = DevVerifier()
        else:
            _verifier = CognitoVerifier(
                region=config.cognito_region,
                user_pool_id=config.cognito_user_pool_id,
                client_id=config.cognito_client_id,
            )
    return _verifier


async def get_current_user(
    config: Annotated[APIConfig, Depends(get_config)],
    verifier: Annotated[TokenVerifier, Depends(get_verifier)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthUser:
    """Extract and verify the bearer token, returning the current user."""
    if config.auth_bypass and config.debug:
        return verifier.verify("")

    if authorization is None:
        raise AuthError("Missing Authorization header")

    parts = authorization.split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Authorization header must be: Bearer <token>")

    return verifier.verify(parts[1])


async def get_project_repo(
    config: Annotated[APIConfig, Depends(get_config)],
) -> ProjectRepository:
    """Return the project repository, creating it on first call."""
    global _project_repo  # noqa: PLW0603
    if _project_repo is None:
        if config.mode == "cloud":
            from openfactcheck.api.repositories.dynamodb.projects import DynamoProjectRepository

            _project_repo = DynamoProjectRepository(config.dynamodb_table_name, config.dynamodb_region)
        else:
            from openfactcheck.api.repositories.sqlite.projects import SqliteProjectRepository

            sf = await _get_sqlite_session_factory(config)
            _project_repo = SqliteProjectRepository(sf)
    return _project_repo


async def get_workspace_repo(
    config: Annotated[APIConfig, Depends(get_config)],
) -> WorkspaceRepository:
    """Return the workspace repository, creating it on first call."""
    global _workspace_repo  # noqa: PLW0603
    if _workspace_repo is None:
        if config.mode == "cloud":
            from openfactcheck.api.repositories.dynamodb.workspaces import DynamoWorkspaceRepository

            _workspace_repo = DynamoWorkspaceRepository(config.dynamodb_table_name, config.dynamodb_region)
        else:
            from openfactcheck.api.repositories.sqlite.workspaces import SqliteWorkspaceRepository

            sf = await _get_sqlite_session_factory(config)
            _workspace_repo = SqliteWorkspaceRepository(sf)
    return _workspace_repo
