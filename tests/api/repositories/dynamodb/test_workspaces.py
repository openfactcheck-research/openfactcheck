"""Tests for DynamoWorkspaceRepository."""

import pytest
import pytest_asyncio

from openfactcheck.api.models import ProjectCreate, WorkspaceCreate, WorkspaceSettings, WorkspaceUpdate
from openfactcheck.api.repositories.dynamodb.projects import DynamoProjectRepository
from openfactcheck.api.repositories.dynamodb.workspaces import MAX_WORKSPACES_PER_PROJECT, DynamoWorkspaceRepository

USER_ID = "user-1"
OTHER_USER = "user-2"
REGION = "us-east-1"

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest_asyncio.fixture(loop_scope="function")
async def project_id(dynamo_table: str) -> str:
    """Create a project and return its ID for workspace tests."""
    repo = DynamoProjectRepository(dynamo_table, region_name=REGION)
    project = await repo.create(USER_ID, ProjectCreate(name="Test Project"))
    return project.id


@pytest.fixture
def repo(dynamo_table: str) -> DynamoWorkspaceRepository:
    return DynamoWorkspaceRepository(dynamo_table, region_name=REGION)


async def test_DynamoWorkspaceRepository_create(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Create returns a workspace with correct fields and sort_order=1."""
    ws = await repo.create(USER_ID, project_id, WorkspaceCreate(name="My Workspace"))

    assert ws is not None
    assert ws.name == "My Workspace"
    assert ws.user_id == USER_ID
    assert ws.project_id == project_id
    assert ws.sort_order == 1
    assert ws.locked is False
    assert ws.description == ""


async def test_DynamoWorkspaceRepository_create_increments_sort_order(
    repo: DynamoWorkspaceRepository, project_id: str
) -> None:
    """Each new workspace gets an incrementing sort_order."""
    ws1 = await repo.create(USER_ID, project_id, WorkspaceCreate(name="First"))
    ws2 = await repo.create(USER_ID, project_id, WorkspaceCreate(name="Second"))

    assert ws1 is not None
    assert ws2 is not None
    assert ws1.sort_order == 1
    assert ws2.sort_order == 2


async def test_DynamoWorkspaceRepository_create_enforces_limit(
    repo: DynamoWorkspaceRepository, project_id: str
) -> None:
    """Create returns None when the project already has MAX_WORKSPACES_PER_PROJECT workspaces."""
    for i in range(MAX_WORKSPACES_PER_PROJECT):
        result = await repo.create(USER_ID, project_id, WorkspaceCreate(name=f"WS {i}"))
        assert result is not None

    overflow = await repo.create(USER_ID, project_id, WorkspaceCreate(name="Overflow"))

    assert overflow is None


async def test_DynamoWorkspaceRepository_get(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Get retrieves a previously created workspace."""
    created = await repo.create(USER_ID, project_id, WorkspaceCreate(name="Test"))
    assert created is not None

    fetched = await repo.get(USER_ID, project_id, created.id)

    assert fetched is not None
    assert fetched.id == created.id


async def test_DynamoWorkspaceRepository_get_wrong_user(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Get returns None when queried by a different user."""
    created = await repo.create(USER_ID, project_id, WorkspaceCreate(name="Test"))
    assert created is not None

    result = await repo.get(OTHER_USER, project_id, created.id)

    assert result is None


async def test_DynamoWorkspaceRepository_list_by_project(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """List returns workspaces ordered by sort_order."""
    await repo.create(USER_ID, project_id, WorkspaceCreate(name="First"))
    await repo.create(USER_ID, project_id, WorkspaceCreate(name="Second"))

    workspaces = await repo.list_by_project(USER_ID, project_id)

    assert len(workspaces) == 2
    assert workspaces[0].name == "First"
    assert workspaces[1].name == "Second"


async def test_DynamoWorkspaceRepository_list_by_project_empty(
    repo: DynamoWorkspaceRepository, project_id: str
) -> None:
    """List returns an empty list when the project has no workspaces."""
    workspaces = await repo.list_by_project(USER_ID, project_id)

    assert workspaces == []


async def test_DynamoWorkspaceRepository_update(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Update modifies fields and bumps updated_at."""
    created = await repo.create(USER_ID, project_id, WorkspaceCreate(name="Old"))
    assert created is not None

    updated = await repo.update(
        USER_ID,
        project_id,
        created.id,
        WorkspaceUpdate(name="New", description="Updated", locked=True, settings=WorkspaceSettings(verbose_mode=True)),
    )

    assert updated is not None
    assert updated.name == "New"
    assert updated.description == "Updated"
    assert updated.locked is True
    assert updated.settings.verbose_mode is True
    assert updated.updated_at > created.updated_at


async def test_DynamoWorkspaceRepository_update_no_fields(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Update with no fields returns the workspace unchanged."""
    created = await repo.create(USER_ID, project_id, WorkspaceCreate(name="Keep"))
    assert created is not None

    updated = await repo.update(USER_ID, project_id, created.id, WorkspaceUpdate())

    assert updated is not None
    assert updated.name == "Keep"


async def test_DynamoWorkspaceRepository_update_nonexistent(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Update returns None for a non-existent workspace."""
    result = await repo.update(USER_ID, project_id, "does-not-exist", WorkspaceUpdate(name="X"))

    assert result is None


async def test_DynamoWorkspaceRepository_delete(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Delete removes the workspace and returns True."""
    created = await repo.create(USER_ID, project_id, WorkspaceCreate(name="To Delete"))
    assert created is not None

    deleted = await repo.delete(USER_ID, project_id, created.id)

    assert deleted is True
    assert await repo.get(USER_ID, project_id, created.id) is None


async def test_DynamoWorkspaceRepository_delete_nonexistent(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Delete returns False when the workspace does not exist."""
    deleted = await repo.delete(USER_ID, project_id, "does-not-exist")

    assert deleted is False


async def test_DynamoWorkspaceRepository_duplicate(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Duplicate creates a copy with '(copy)' suffix and a new ID."""
    original = await repo.create(USER_ID, project_id, WorkspaceCreate(name="Original"))
    assert original is not None

    copy = await repo.duplicate(USER_ID, project_id, original.id)

    assert copy is not None
    assert copy.id != original.id
    assert copy.name == "Original (copy)"
    assert copy.sort_order == 2
    assert copy.locked is False


async def test_DynamoWorkspaceRepository_duplicate_nonexistent(
    repo: DynamoWorkspaceRepository, project_id: str
) -> None:
    """Duplicate returns None when the source workspace does not exist."""
    result = await repo.duplicate(USER_ID, project_id, "does-not-exist")

    assert result is None


async def test_DynamoWorkspaceRepository_duplicate_enforces_limit(
    repo: DynamoWorkspaceRepository, project_id: str
) -> None:
    """Duplicate returns None when the project is at the workspace limit."""
    first = await repo.create(USER_ID, project_id, WorkspaceCreate(name="First"))
    assert first is not None
    for i in range(1, MAX_WORKSPACES_PER_PROJECT):
        await repo.create(USER_ID, project_id, WorkspaceCreate(name=f"WS {i}"))

    result = await repo.duplicate(USER_ID, project_id, first.id)

    assert result is None


async def test_DynamoWorkspaceRepository_reorder(repo: DynamoWorkspaceRepository, project_id: str) -> None:
    """Reorder updates sort_order to match the provided ID list."""
    ws1 = await repo.create(USER_ID, project_id, WorkspaceCreate(name="A"))
    ws2 = await repo.create(USER_ID, project_id, WorkspaceCreate(name="B"))
    ws3 = await repo.create(USER_ID, project_id, WorkspaceCreate(name="C"))
    assert ws1 and ws2 and ws3

    await repo.reorder(USER_ID, project_id, [ws3.id, ws1.id, ws2.id])

    workspaces = await repo.list_by_project(USER_ID, project_id)
    assert [ws.name for ws in workspaces] == ["C", "A", "B"]
