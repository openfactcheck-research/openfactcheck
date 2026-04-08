"""Tests for SqliteProjectRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import ProjectCreate, ProjectUpdate
from openfactcheck.api.repositories.sqlite.projects import SqliteProjectRepository

USER_ID = "user-1"
OTHER_USER = "user-2"

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest.fixture
def repo(db_session_factory: async_sessionmaker[AsyncSession]) -> SqliteProjectRepository:
    return SqliteProjectRepository(db_session_factory)


async def test_SqliteProjectRepository_create(repo: SqliteProjectRepository) -> None:
    """Create returns a project with the correct name and user."""
    project = await repo.create(USER_ID, ProjectCreate(name="My Project"))

    assert project.name == "My Project"
    assert project.user_id == USER_ID
    assert len(project.id) == 12


async def test_SqliteProjectRepository_get(repo: SqliteProjectRepository) -> None:
    """Get retrieves a previously created project."""
    created = await repo.create(USER_ID, ProjectCreate(name="Test"))

    fetched = await repo.get(USER_ID, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Test"


async def test_SqliteProjectRepository_get_wrong_user(repo: SqliteProjectRepository) -> None:
    """Get returns None when queried by a different user."""
    created = await repo.create(USER_ID, ProjectCreate(name="Test"))

    result = await repo.get(OTHER_USER, created.id)

    assert result is None


async def test_SqliteProjectRepository_get_nonexistent(repo: SqliteProjectRepository) -> None:
    """Get returns None for a non-existent project ID."""
    result = await repo.get(USER_ID, "does-not-exist")

    assert result is None


async def test_SqliteProjectRepository_list_by_user(repo: SqliteProjectRepository) -> None:
    """List returns only projects belonging to the given user, ordered by created_at."""
    await repo.create(USER_ID, ProjectCreate(name="First"))
    await repo.create(USER_ID, ProjectCreate(name="Second"))
    await repo.create(OTHER_USER, ProjectCreate(name="Other"))

    projects = await repo.list_by_user(USER_ID)

    assert len(projects) == 2
    assert projects[0].name == "First"
    assert projects[1].name == "Second"


async def test_SqliteProjectRepository_list_by_user_empty(repo: SqliteProjectRepository) -> None:
    """List returns an empty list when the user has no projects."""
    projects = await repo.list_by_user(USER_ID)

    assert projects == []


async def test_SqliteProjectRepository_update(repo: SqliteProjectRepository) -> None:
    """Update modifies the project name and bumps updated_at."""
    created = await repo.create(USER_ID, ProjectCreate(name="Old Name"))

    updated = await repo.update(USER_ID, created.id, ProjectUpdate(name="New Name"))

    assert updated is not None
    assert updated.name == "New Name"
    assert updated.updated_at > created.updated_at


async def test_SqliteProjectRepository_update_no_fields(repo: SqliteProjectRepository) -> None:
    """Update with no fields returns the project unchanged."""
    created = await repo.create(USER_ID, ProjectCreate(name="Keep"))

    updated = await repo.update(USER_ID, created.id, ProjectUpdate())

    assert updated is not None
    assert updated.name == "Keep"


async def test_SqliteProjectRepository_update_nonexistent(repo: SqliteProjectRepository) -> None:
    """Update returns None for a non-existent project."""
    result = await repo.update(USER_ID, "does-not-exist", ProjectUpdate(name="X"))

    assert result is None


async def test_SqliteProjectRepository_delete(repo: SqliteProjectRepository) -> None:
    """Delete removes the project and returns True."""
    created = await repo.create(USER_ID, ProjectCreate(name="To Delete"))

    deleted = await repo.delete(USER_ID, created.id)

    assert deleted is True
    assert await repo.get(USER_ID, created.id) is None


async def test_SqliteProjectRepository_delete_nonexistent(repo: SqliteProjectRepository) -> None:
    """Delete returns False when the project does not exist."""
    deleted = await repo.delete(USER_ID, "does-not-exist")

    assert deleted is False


async def test_SqliteProjectRepository_delete_wrong_user(repo: SqliteProjectRepository) -> None:
    """Delete returns False when attempted by a different user."""
    created = await repo.create(USER_ID, ProjectCreate(name="Mine"))

    deleted = await repo.delete(OTHER_USER, created.id)

    assert deleted is False
    assert await repo.get(USER_ID, created.id) is not None
