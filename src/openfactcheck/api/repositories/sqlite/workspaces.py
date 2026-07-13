"""SQLite-backed workspace repository."""

import json
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import (
    Workspace,
    WorkspaceCreate,
    WorkspaceUpdate,
)
from openfactcheck.api.repositories.constants import (
    MAX_WORKSPACES_PER_PROJECT,
    generate_id,
)
from openfactcheck.api.repositories.sqlite.helpers import row_to_dict
from openfactcheck.api.repositories.sqlite.tables import WorkspaceRow


class SqliteWorkspaceRepository:
    """SQLite-backed repository for workspace CRUD, duplication, and reordering."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Build a repository that opens sessions from the given factory.

        Args:
            session_factory: Async session factory bound to a SQLite engine.
        """
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
        """List the project's workspaces, ordered by ``sort_order`` (display order)."""
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
        """Return the workspace, or ``None`` if no workspace with that ID exists in the project."""
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
        """Create a new workspace at the end of the project's sort order.

        Returns ``None`` if the project has already reached
        [`MAX_WORKSPACES_PER_PROJECT`][MAX_WORKSPACES_PER_PROJECT].
        """
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
        """Apply a partial update and return the updated workspace, or ``None`` if it doesn't exist.

        An update with no fields set returns the workspace unchanged.
        """
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
        """Delete the workspace. Returns ``False`` if it doesn't exist."""
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
        """Copy the workspace and append ``(copy)`` to its name.

        Returns ``None`` if the source workspace doesn't exist, or if the project has already reached
        [`MAX_WORKSPACES_PER_PROJECT`][MAX_WORKSPACES_PER_PROJECT].
        """
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
        """Reassign ``sort_order`` for the listed workspaces in the given sequence.

        Each ID in ``ordered_ids`` is numbered ``1..N``. IDs not in the list keep
        their current ``sort_order``.
        """
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
