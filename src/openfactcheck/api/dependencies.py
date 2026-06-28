"""FastAPI dependency injection: settings, auth, repositories."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header

from openfactcheck.api.auth.cognito import CognitoVerifier
from openfactcheck.api.auth.dev import DevVerifier
from openfactcheck.api.auth.protocols import TokenVerifier
from openfactcheck.api.config import APIConfig
from openfactcheck.api.crypto.protocols import SecretCipher
from openfactcheck.api.errors import AuthError
from openfactcheck.api.models import AuthUser
from openfactcheck.api.repositories.protocols import (
    PreferencesRepository,
    ProjectRepository,
    SecretRepository,
    WorkspaceRepository,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_config() -> APIConfig:
    """Return the singleton API configuration."""
    return APIConfig()


class _State:
    """Lazy singletons for dependency injection."""

    verifier: TokenVerifier | None = None
    project_repo: ProjectRepository | None = None
    workspace_repo: WorkspaceRepository | None = None
    secret_repo: SecretRepository | None = None
    preferences_repo: PreferencesRepository | None = None
    cipher: SecretCipher | None = None


_state = _State()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def get_verifier(
    config: Annotated[APIConfig, Depends(get_config)],
) -> TokenVerifier:
    """Return the token verifier, creating it on first call."""
    if _state.verifier is None:
        if config.auth_bypass and config.debug:
            _state.verifier = DevVerifier()
        else:
            _state.verifier = CognitoVerifier(
                region=config.cognito_region,
                user_pool_id=config.cognito_user_pool_id,
                client_id=config.cognito_client_id,
            )
    return _state.verifier


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

    try:
        scheme, token = authorization.split(" ", maxsplit=1)
    except ValueError:
        raise AuthError("Authorization header must be: Bearer <token>") from None
    if scheme.lower() != "bearer":
        raise AuthError("Authorization header must be: Bearer <token>")

    return verifier.verify(token)


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


async def _init_repos(config: APIConfig) -> None:
    """Wire up all repository singletons based on config mode."""
    if config.mode == "cloud":
        from openfactcheck.api.repositories.dynamodb.preferences import (  # noqa: PLC0415 - lazy import for optional backend.
            DynamoPreferencesRepository,
        )
        from openfactcheck.api.repositories.dynamodb.projects import (  # noqa: PLC0415 - lazy import for optional backend.
            DynamoProjectRepository,
        )
        from openfactcheck.api.repositories.dynamodb.secrets import (  # noqa: PLC0415 - lazy import for optional backend.
            DynamoSecretRepository,
        )
        from openfactcheck.api.repositories.dynamodb.workspaces import (  # noqa: PLC0415 - lazy import for optional backend.
            DynamoWorkspaceRepository,
        )

        _state.project_repo = DynamoProjectRepository(config.dynamodb_table_name, config.dynamodb_region)
        _state.workspace_repo = DynamoWorkspaceRepository(config.dynamodb_table_name, config.dynamodb_region)
        _state.secret_repo = DynamoSecretRepository(config.dynamodb_users_table_name, config.dynamodb_region)
        _state.preferences_repo = DynamoPreferencesRepository(config.dynamodb_users_table_name, config.dynamodb_region)
    else:
        from openfactcheck.api.repositories.sqlite.engine import (  # noqa: PLC0415 - lazy import for optional backend.
            create_engine,
            create_session_factory,
            create_tables,
        )
        from openfactcheck.api.repositories.sqlite.preferences import (  # noqa: PLC0415 - lazy import for optional backend.
            SqlitePreferencesRepository,
        )
        from openfactcheck.api.repositories.sqlite.projects import (  # noqa: PLC0415 - lazy import for optional backend.
            SqliteProjectRepository,
        )
        from openfactcheck.api.repositories.sqlite.secrets import (  # noqa: PLC0415 - lazy import for optional backend.
            SqliteSecretRepository,
        )
        from openfactcheck.api.repositories.sqlite.workspaces import (  # noqa: PLC0415 - lazy import for optional backend.
            SqliteWorkspaceRepository,
        )

        engine = create_engine(config.sqlite_path)
        await create_tables(engine)
        sf = create_session_factory(engine)
        _state.project_repo = SqliteProjectRepository(sf)
        _state.workspace_repo = SqliteWorkspaceRepository(sf)
        _state.secret_repo = SqliteSecretRepository(sf)
        _state.preferences_repo = SqlitePreferencesRepository(sf)


async def get_project_repo(
    config: Annotated[APIConfig, Depends(get_config)],
) -> ProjectRepository:
    """Return the project repository."""
    if _state.project_repo is None:
        await _init_repos(config)
    if _state.project_repo is None:
        raise RuntimeError("Failed to initialize project repository")
    return _state.project_repo


async def get_workspace_repo(
    config: Annotated[APIConfig, Depends(get_config)],
) -> WorkspaceRepository:
    """Return the workspace repository."""
    if _state.workspace_repo is None:
        await _init_repos(config)
    if _state.workspace_repo is None:
        raise RuntimeError("Failed to initialize workspace repository")
    return _state.workspace_repo


async def get_secret_repo(
    config: Annotated[APIConfig, Depends(get_config)],
) -> SecretRepository:
    """Return the secret repository."""
    if _state.secret_repo is None:
        await _init_repos(config)
    if _state.secret_repo is None:
        raise RuntimeError("Failed to initialize secret repository")
    return _state.secret_repo


async def get_preferences_repo(
    config: Annotated[APIConfig, Depends(get_config)],
) -> PreferencesRepository:
    """Return the preferences repository."""
    if _state.preferences_repo is None:
        await _init_repos(config)
    if _state.preferences_repo is None:
        raise RuntimeError("Failed to initialize preferences repository")
    return _state.preferences_repo


# ---------------------------------------------------------------------------
# Cipher
# ---------------------------------------------------------------------------


async def get_cipher(
    config: Annotated[APIConfig, Depends(get_config)],
) -> SecretCipher:
    """Return the secret cipher for the configured mode, creating it on first call."""
    if _state.cipher is None:
        if config.mode == "cloud":
            from openfactcheck.api.crypto.kms import (  # noqa: PLC0415 - lazy import for optional cloud backend.
                KmsCipher,
            )

            _state.cipher = KmsCipher(config.secrets_kms_key_id, config.dynamodb_region)
        else:
            from openfactcheck.api.crypto.local import (  # noqa: PLC0415 - lazy import for optional backend.
                LocalCipher,
            )

            _state.cipher = LocalCipher(config.secrets_key_path)
    return _state.cipher
