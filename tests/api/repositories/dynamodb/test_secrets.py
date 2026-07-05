"""Tests for DynamoSecretRepository."""

import pytest

from openfactcheck.api.repositories.dynamodb.secrets import MAX_SECRETS_PER_USER, DynamoSecretRepository

USER_ID = "user-1"
OTHER_USER = "user-2"
REGION = "us-east-1"

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest.fixture
def repo(dynamo_table: str) -> DynamoSecretRepository:
    return DynamoSecretRepository(dynamo_table, region_name=REGION)


async def test_DynamoSecretRepository_set_returns_masked_secret(repo: DynamoSecretRepository) -> None:
    """Set returns the secret's name and hint, never its value."""
    secret = await repo.set(USER_ID, "openai", "ciphertext-abc", "wxyz")

    assert secret is not None
    assert secret.name == "openai"
    assert secret.hint == "wxyz"
    assert "ciphertext" not in secret.model_dump()


async def test_DynamoSecretRepository_list_is_sorted_and_masked(repo: DynamoSecretRepository) -> None:
    """List returns the user's secrets ordered by name, without ciphertext."""
    await repo.set(USER_ID, "openrouter", "ct-2", "2222")
    await repo.set(USER_ID, "anthropic", "ct-1", "1111")

    secrets = await repo.list(USER_ID)

    assert [s.name for s in secrets] == ["anthropic", "openrouter"]
    assert set(secrets[0].model_dump()) == {"name", "hint", "created_at", "updated_at"}


async def test_DynamoSecretRepository_get_ciphertext(repo: DynamoSecretRepository) -> None:
    """Get-ciphertext returns the stored ciphertext, or None when unset."""
    await repo.set(USER_ID, "openai", "ciphertext-abc", "wxyz")

    assert await repo.get_ciphertext(USER_ID, "openai") == "ciphertext-abc"
    assert await repo.get_ciphertext(USER_ID, "missing") is None


async def test_DynamoSecretRepository_set_replaces_and_keeps_created_at(repo: DynamoSecretRepository) -> None:
    """Replacing a secret keeps created_at and does not move updated_at backwards."""
    first = await repo.set(USER_ID, "openai", "ct-1", "1111")
    second = await repo.set(USER_ID, "openai", "ct-2", "2222")

    assert first is not None
    assert second is not None
    assert second.created_at == first.created_at
    assert second.updated_at >= first.updated_at
    assert await repo.get_ciphertext(USER_ID, "openai") == "ct-2"


async def test_DynamoSecretRepository_set_enforces_limit(repo: DynamoSecretRepository) -> None:
    """Set returns None for a new secret past the limit, but still replaces existing ones."""
    for i in range(MAX_SECRETS_PER_USER):
        assert await repo.set(USER_ID, f"key_{i}", "ct", "hint") is not None

    assert await repo.set(USER_ID, "one_too_many", "ct", "hint") is None
    assert await repo.set(USER_ID, "key_0", "ct-new", "new") is not None


async def test_DynamoSecretRepository_delete(repo: DynamoSecretRepository) -> None:
    """Delete removes a secret and reports whether one was deleted."""
    await repo.set(USER_ID, "openai", "ct", "hint")

    assert await repo.delete(USER_ID, "openai") is True
    assert await repo.delete(USER_ID, "openai") is False
    assert await repo.list(USER_ID) == []


async def test_DynamoSecretRepository_scopes_to_user(repo: DynamoSecretRepository) -> None:
    """Secrets are isolated per user."""
    await repo.set(USER_ID, "openai", "ct", "hint")

    assert await repo.list(OTHER_USER) == []
    assert await repo.get_ciphertext(OTHER_USER, "openai") is None


async def test_DynamoSecretRepository_scopes_to_project(repo: DynamoSecretRepository) -> None:
    """A project override is stored separately from the global secret of the same name."""
    await repo.set(USER_ID, "openai", "global-ct", "glob")
    await repo.set(USER_ID, "openai", "project-ct", "proj", project_id="p1")

    assert await repo.get_ciphertext(USER_ID, "openai") == "global-ct"
    assert await repo.get_ciphertext(USER_ID, "openai", project_id="p1") == "project-ct"
    assert [s.name for s in await repo.list(USER_ID, project_id="p1")] == ["openai"]

    assert await repo.delete(USER_ID, "openai", project_id="p1") is True
    assert await repo.get_ciphertext(USER_ID, "openai", project_id="p1") is None
    assert await repo.get_ciphertext(USER_ID, "openai") == "global-ct"  # global intact
