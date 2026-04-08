"""SQLite implementation of the project repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import Project, ProjectCreate, ProjectUpdate
from openfactcheck.api.repositories.constants import MAX_PROJECTS_PER_USER, generate_id
from openfactcheck.api.repositories.sqlite.tables import ProjectRow


def _row_to_model(row: ProjectRow) -> Project:
    return Project(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        created_at=row.created_at.replace(tzinfo=UTC),
        updated_at=row.updated_at.replace(tzinfo=UTC),
    )


class SqliteProjectRepository:
    """Project CRUD backed by SQLite via SQLAlchemy async."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Project]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProjectRow)
                .where(ProjectRow.user_id == user_id)
                .order_by(ProjectRow.created_at)
                .limit(limit)
                .offset(offset)
            )
            return [_row_to_model(row) for row in result.scalars()]

    async def get(self, user_id: str, project_id: str) -> Project | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProjectRow).where(ProjectRow.id == project_id, ProjectRow.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            return _row_to_model(row) if row else None

    async def create(self, user_id: str, data: ProjectCreate) -> Project | None:
        async with self._session_factory() as session:
            count_result = await session.execute(
                select(func.count()).select_from(ProjectRow).where(ProjectRow.user_id == user_id)
            )
            if count_result.scalar_one() >= MAX_PROJECTS_PER_USER:
                return None

            now = datetime.now(UTC)
            row = ProjectRow(
                id=generate_id(),
                user_id=user_id,
                name=data.name,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            return _row_to_model(row)

    async def update(self, user_id: str, project_id: str, data: ProjectUpdate) -> Project | None:
        values = data.model_dump(exclude_none=True)
        if not values:
            return await self.get(user_id, project_id)

        values["updated_at"] = datetime.now(UTC)

        async with self._session_factory() as session:
            cursor = await session.execute(
                update(ProjectRow).where(ProjectRow.id == project_id, ProjectRow.user_id == user_id).values(**values)
            )
            await session.commit()
            if cursor.rowcount == 0:  # type: ignore[union-attr]
                return None

        return await self.get(user_id, project_id)

    async def delete(self, user_id: str, project_id: str) -> bool:
        async with self._session_factory() as session:
            cursor = await session.execute(
                delete(ProjectRow).where(ProjectRow.id == project_id, ProjectRow.user_id == user_id)
            )
            await session.commit()
            return bool(cursor.rowcount)  # type: ignore[union-attr]
