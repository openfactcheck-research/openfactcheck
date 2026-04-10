"""Tests for SqliteRunRepository."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import ProjectCreate, RunCreate, RunStatus, WorkspaceCreate
from openfactcheck.api.repositories.sqlite.projects import SqliteProjectRepository
from openfactcheck.api.repositories.sqlite.runs import SqliteRunRepository
from openfactcheck.api.repositories.sqlite.workspaces import SqliteWorkspaceRepository

USER_ID = "user-1"
OTHER_USER = "user-2"

pytestmark = pytest.mark.asyncio(loop_scope="function")

SAMPLE_PIPELINE = {"blocks": {"blocks": [{"type": "text_print", "id": "abc"}]}}


@pytest_asyncio.fixture(loop_scope="function")
async def project_id(db_session_factory: async_sessionmaker[AsyncSession]) -> str:
    repo = SqliteProjectRepository(db_session_factory)
    project = await repo.create(USER_ID, ProjectCreate(name="Test Project"))
    assert project is not None
    return project.id


@pytest_asyncio.fixture(loop_scope="function")
async def workspace_id(db_session_factory: async_sessionmaker[AsyncSession], project_id: str) -> str:
    repo = SqliteWorkspaceRepository(db_session_factory)
    ws = await repo.create(USER_ID, project_id, WorkspaceCreate(name="Test Workspace"))
    assert ws is not None
    return ws.id


@pytest.fixture
def repo(db_session_factory: async_sessionmaker[AsyncSession]) -> SqliteRunRepository:
    return SqliteRunRepository(db_session_factory)


async def test_create(repo: SqliteRunRepository, project_id: str, workspace_id: str) -> None:
    run = await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))

    assert run.user_id == USER_ID
    assert run.project_id == project_id
    assert run.workspace_id == workspace_id
    assert run.status == RunStatus.PENDING
    assert run.pipeline == SAMPLE_PIPELINE
    assert run.output is None
    assert run.error is None
    assert run.started_at is None
    assert run.completed_at is None


async def test_get(repo: SqliteRunRepository, project_id: str, workspace_id: str) -> None:
    created = await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))

    fetched = await repo.get(USER_ID, project_id, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.status == RunStatus.PENDING


async def test_get_wrong_user(repo: SqliteRunRepository, project_id: str, workspace_id: str) -> None:
    created = await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))

    result = await repo.get(OTHER_USER, project_id, created.id)

    assert result is None


async def test_get_nonexistent(repo: SqliteRunRepository, project_id: str) -> None:
    result = await repo.get(USER_ID, project_id, "does-not-exist")

    assert result is None


async def test_update_status_running(repo: SqliteRunRepository, project_id: str, workspace_id: str) -> None:
    created = await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))

    updated = await repo.update_status(USER_ID, project_id, created.id, RunStatus.RUNNING)

    assert updated is not None
    assert updated.status == RunStatus.RUNNING
    assert updated.started_at is not None
    assert updated.completed_at is None


async def test_update_status_completed(repo: SqliteRunRepository, project_id: str, workspace_id: str) -> None:
    created = await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))
    await repo.update_status(USER_ID, project_id, created.id, RunStatus.RUNNING)

    updated = await repo.update_status(
        USER_ID, project_id, created.id, RunStatus.COMPLETED, output="Hello World"
    )

    assert updated is not None
    assert updated.status == RunStatus.COMPLETED
    assert updated.output == "Hello World"
    assert updated.completed_at is not None


async def test_update_status_failed(repo: SqliteRunRepository, project_id: str, workspace_id: str) -> None:
    created = await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))

    updated = await repo.update_status(
        USER_ID, project_id, created.id, RunStatus.FAILED, error="Something went wrong"
    )

    assert updated is not None
    assert updated.status == RunStatus.FAILED
    assert updated.error == "Something went wrong"
    assert updated.completed_at is not None


async def test_update_status_nonexistent(repo: SqliteRunRepository, project_id: str) -> None:
    result = await repo.update_status(USER_ID, project_id, "does-not-exist", RunStatus.RUNNING)

    assert result is None


async def test_list_by_project(repo: SqliteRunRepository, project_id: str, workspace_id: str) -> None:
    await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))
    await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))

    runs = await repo.list_by_project(USER_ID, project_id)

    assert len(runs) == 2


async def test_list_by_project_empty(repo: SqliteRunRepository, project_id: str) -> None:
    runs = await repo.list_by_project(USER_ID, project_id)

    assert runs == []


async def test_list_by_project_filters_by_workspace(
    repo: SqliteRunRepository, project_id: str, workspace_id: str, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    ws_repo = SqliteWorkspaceRepository(db_session_factory)
    ws2 = await ws_repo.create(USER_ID, project_id, WorkspaceCreate(name="Other Workspace"))
    assert ws2 is not None

    await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))
    await repo.create(USER_ID, project_id, RunCreate(workspace_id=ws2.id, pipeline=SAMPLE_PIPELINE))

    runs = await repo.list_by_project(USER_ID, project_id, workspace_id=workspace_id)

    assert len(runs) == 1
    assert runs[0].workspace_id == workspace_id


async def test_list_by_project_ordered_newest_first(
    repo: SqliteRunRepository, project_id: str, workspace_id: str
) -> None:
    r1 = await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))
    r2 = await repo.create(USER_ID, project_id, RunCreate(workspace_id=workspace_id, pipeline=SAMPLE_PIPELINE))

    runs = await repo.list_by_project(USER_ID, project_id)

    assert runs[0].id == r2.id
    assert runs[1].id == r1.id
