"""Tests for DynamoProjectRepository."""

import pytest

from openfactcheck.api.models import ProjectCreate, ProjectUpdate
from openfactcheck.api.repositories.dynamodb.projects import DynamoProjectRepository

USER_ID = "user-1"
OTHER_USER = "user-2"
REGION = "us-east-1"

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest.fixture
def repo(dynamo_table: str) -> DynamoProjectRepository:
    return DynamoProjectRepository(dynamo_table, region_name=REGION)


async def test_DynamoProjectRepository_create(repo: DynamoProjectRepository) -> None:
    """Create returns a project with the correct name and user."""
    project = await repo.create(USER_ID, ProjectCreate(name="My Project"))

    assert project.name == "My Project"
    assert project.user_id == USER_ID
    assert len(project.id) == 12


async def test_DynamoProjectRepository_get(repo: DynamoProjectRepository) -> None:
    """Get retrieves a previously created project."""
    created = await repo.create(USER_ID, ProjectCreate(name="Test"))

    fetched = await repo.get(USER_ID, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Test"


async def test_DynamoProjectRepository_get_wrong_user(repo: DynamoProjectRepository) -> None:
    """Get returns None when queried by a different user."""
    created = await repo.create(USER_ID, ProjectCreate(name="Test"))

    result = await repo.get(OTHER_USER, created.id)

    assert result is None


async def test_DynamoProjectRepository_get_nonexistent(repo: DynamoProjectRepository) -> None:
    """Get returns None for a non-existent project ID."""
    result = await repo.get(USER_ID, "does-not-exist")

    assert result is None


async def test_DynamoProjectRepository_list_by_user(repo: DynamoProjectRepository) -> None:
    """List returns only projects belonging to the given user, ordered by created_at."""
    await repo.create(USER_ID, ProjectCreate(name="First"))
    await repo.create(USER_ID, ProjectCreate(name="Second"))
    await repo.create(OTHER_USER, ProjectCreate(name="Other"))

    projects = await repo.list_by_user(USER_ID)

    assert len(projects) == 2
    assert projects[0].name == "First"
    assert projects[1].name == "Second"


async def test_DynamoProjectRepository_list_by_user_empty(repo: DynamoProjectRepository) -> None:
    """List returns an empty list when the user has no projects."""
    projects = await repo.list_by_user(USER_ID)

    assert projects == []


async def test_DynamoProjectRepository_update(repo: DynamoProjectRepository) -> None:
    """Update modifies the project name and bumps updated_at."""
    created = await repo.create(USER_ID, ProjectCreate(name="Old Name"))

    updated = await repo.update(USER_ID, created.id, ProjectUpdate(name="New Name"))

    assert updated is not None
    assert updated.name == "New Name"
    assert updated.updated_at > created.updated_at


async def test_DynamoProjectRepository_update_no_fields(repo: DynamoProjectRepository) -> None:
    """Update with no fields returns the project unchanged."""
    created = await repo.create(USER_ID, ProjectCreate(name="Keep"))

    updated = await repo.update(USER_ID, created.id, ProjectUpdate())

    assert updated is not None
    assert updated.name == "Keep"


async def test_DynamoProjectRepository_update_nonexistent(repo: DynamoProjectRepository) -> None:
    """Update returns None for a non-existent project."""
    result = await repo.update(USER_ID, "does-not-exist", ProjectUpdate(name="X"))

    assert result is None


async def test_DynamoProjectRepository_delete(repo: DynamoProjectRepository) -> None:
    """Delete removes the project and returns True."""
    created = await repo.create(USER_ID, ProjectCreate(name="To Delete"))

    deleted = await repo.delete(USER_ID, created.id)

    assert deleted is True
    assert await repo.get(USER_ID, created.id) is None


async def test_DynamoProjectRepository_delete_nonexistent(repo: DynamoProjectRepository) -> None:
    """Delete returns False when the project does not exist."""
    deleted = await repo.delete(USER_ID, "does-not-exist")

    assert deleted is False
