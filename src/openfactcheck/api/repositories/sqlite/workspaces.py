"""SQLite implementation of the workspace repository."""

import json
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import (
    Workspace,
    WorkspaceCreate,
    WorkspaceRun,
    WorkspaceUpdate,
)
from openfactcheck.api.repositories.constants import (
    MAX_WORKSPACES_PER_PROJECT,
    generate_id,
)
from openfactcheck.api.repositories.sqlite.helpers import row_to_dict
from openfactcheck.api.repositories.sqlite.tables import WorkspaceRow


class SqliteWorkspaceRepository:
    """Workspace CRUD backed by SQLite via SQLAlchemy async."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def _count(self, session: AsyncSession, user_id: str, project_id: str) -> int:
        result = await session.execute(
            select(func.count())
            .select_from(WorkspaceRow)
            .where(WorkspaceRow.user_id == user_id, WorkspaceRow.project_id == project_id),
        )
        return result.scalar_one()

    async def _next_sort_order(self, session: AsyncSession, user_id: str, project_id: str) -> int:
        result = await session.execute(
            select(func.coalesce(func.max(WorkspaceRow.sort_order), 0))
            .select_from(WorkspaceRow)
            .where(WorkspaceRow.user_id == user_id, WorkspaceRow.project_id == project_id),
        )
        return result.scalar_one() + 1

    async def list_by_project(self, user_id: str, project_id: str) -> list[Workspace]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkspaceRow)
                .where(
                    WorkspaceRow.user_id == user_id,
                    WorkspaceRow.project_id == project_id,
                )
                .order_by(WorkspaceRow.sort_order),
            )
            return [Workspace.model_validate(row_to_dict(row)) for row in result.scalars()]

    async def get(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkspaceRow).where(
                    WorkspaceRow.id == workspace_id,
                    WorkspaceRow.user_id == user_id,
                    WorkspaceRow.project_id == project_id,
                ),
            )
            row = result.scalar_one_or_none()
            return Workspace.model_validate(row_to_dict(row)) if row else None

    async def create(self, user_id: str, project_id: str, data: WorkspaceCreate) -> Workspace | None:
        async with self._session_factory() as session:
            if await self._count(session, user_id, project_id) >= MAX_WORKSPACES_PER_PROJECT:
                return None

            now = datetime.now(UTC)
            row = WorkspaceRow(
                id=generate_id(),
                user_id=user_id,
                project_id=project_id,
                name=data.name,
                description=data.description,
                locked=False,
                sort_order=await self._next_sort_order(session, user_id, project_id),
                settings_json="{}",
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            return Workspace.model_validate(row_to_dict(row))

    async def update(self, user_id: str, project_id: str, workspace_id: str, data: WorkspaceUpdate) -> Workspace | None:
        values: dict[str, object] = {}
        if data.name is not None:
            values["name"] = data.name
        if data.description is not None:
            values["description"] = data.description
        if data.locked is not None:
            values["locked"] = data.locked
        if data.settings is not None:
            values["settings_json"] = data.settings.model_dump_json()
        if data.content is not None:
            values["content_json"] = json.dumps(data.content)

        if not values:
            return await self.get(user_id, project_id, workspace_id)

        values["updated_at"] = datetime.now(UTC)

        async with self._session_factory() as session:
            cursor = await session.execute(
                update(WorkspaceRow)
                .where(
                    WorkspaceRow.id == workspace_id,
                    WorkspaceRow.user_id == user_id,
                    WorkspaceRow.project_id == project_id,
                )
                .values(**values),
            )
            await session.commit()
            if cursor.rowcount == 0:
                return None

        return await self.get(user_id, project_id, workspace_id)

    async def delete(self, user_id: str, project_id: str, workspace_id: str) -> bool:
        async with self._session_factory() as session:
            cursor = await session.execute(
                delete(WorkspaceRow).where(
                    WorkspaceRow.id == workspace_id,
                    WorkspaceRow.user_id == user_id,
                    WorkspaceRow.project_id == project_id,
                ),
            )
            await session.commit()
            return bool(cursor.rowcount)

    async def duplicate(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None:
        source = await self.get(user_id, project_id, workspace_id)
        if source is None:
            return None

        async with self._session_factory() as session:
            if await self._count(session, user_id, project_id) >= MAX_WORKSPACES_PER_PROJECT:
                return None

            now = datetime.now(UTC)
            row = WorkspaceRow(
                id=generate_id(),
                user_id=user_id,
                project_id=project_id,
                name=f"{source.name[:248]} (copy)",
                description=source.description,
                locked=False,
                sort_order=await self._next_sort_order(session, user_id, project_id),
                settings_json=json.dumps(source.settings.model_dump()),
                content_json=json.dumps(source.content) if source.content else "{}",
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            return Workspace.model_validate(row_to_dict(row))

    async def reorder(self, user_id: str, project_id: str, ordered_ids: list[str]) -> None:
        async with self._session_factory() as session:
            for index, ws_id in enumerate(ordered_ids, start=1):
                await session.execute(
                    update(WorkspaceRow)
                    .where(
                        WorkspaceRow.id == ws_id,
                        WorkspaceRow.user_id == user_id,
                        WorkspaceRow.project_id == project_id,
                    )
                    .values(sort_order=index, updated_at=datetime.now(UTC)),
                )
            await session.commit()

    async def set_run(self, user_id: str, project_id: str, workspace_id: str, run: WorkspaceRun) -> None:
        """Update the latest run state on the workspace."""
        async with self._session_factory() as session:
            await session.execute(
                update(WorkspaceRow)
                .where(
                    WorkspaceRow.id == workspace_id,
                    WorkspaceRow.user_id == user_id,
                    WorkspaceRow.project_id == project_id,
                )
                .values(run_json=run.model_dump_json(), updated_at=datetime.now(UTC)),
            )
            await session.commit()
