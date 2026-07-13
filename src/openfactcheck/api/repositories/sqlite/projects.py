"""SQLite-backed project repository."""

from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import Project, ProjectCreate, ProjectUpdate
from openfactcheck.api.repositories.constants import MAX_PROJECTS_PER_USER, generate_id
from openfactcheck.api.repositories.sqlite.helpers import row_to_dict
from openfactcheck.api.repositories.sqlite.tables import ProjectRow


class SqliteProjectRepository:
    """SQLite-backed repository for project CRUD."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Build a repository that opens sessions from the given factory.

        Args:
            session_factory: Async session factory bound to a SQLite engine.
        """
        self._session_factory = session_factory

    async def list_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Project]:
        """List the user's projects, ordered by creation time (oldest first)."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProjectRow)
                .where(ProjectRow.user_id == user_id)
                .order_by(ProjectRow.created_at)
                .limit(limit)
                .offset(offset),
            )
            return [Project.model_validate(row_to_dict(row)) for row in result.scalars()]

    async def get(self, user_id: str, project_id: str) -> Project | None:
        """Return the project, or ``None`` if no project with that ID exists for the user."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProjectRow).where(ProjectRow.id == project_id, ProjectRow.user_id == user_id),
            )
            row = result.scalar_one_or_none()
            return Project.model_validate(row_to_dict(row)) if row else None

    async def create(self, user_id: str, data: ProjectCreate) -> Project | None:
        """Create a new project for the user.

        Returns ``None`` if the user has already reached [`MAX_PROJECTS_PER_USER`][MAX_PROJECTS_PER_USER].
        """
        async with self._session_factory() as session:
            count_result = await session.execute(
                select(func.count()).select_from(ProjectRow).where(ProjectRow.user_id == user_id),
            )
            if count_result.scalar_one() >= MAX_PROJECTS_PER_USER:
                return None

            now = datetime.now(UTC)
            row = ProjectRow(
                id=generate_id(),
                user_id=user_id,
                name=data.name,
                description=data.description,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            return Project.model_validate(row_to_dict(row))

    async def update(self, user_id: str, project_id: str, data: ProjectUpdate) -> Project | None:
        """Apply a partial update and return the updated project, or ``None`` if it doesn't exist.

        An update with no fields set returns the project unchanged.
        """
        values = data.model_dump(exclude_none=True)
        if not values:
            return await self.get(user_id, project_id)

        values["updated_at"] = datetime.now(UTC)

        async with self._session_factory() as session:
            cursor = await session.execute(
                update(ProjectRow).where(ProjectRow.id == project_id, ProjectRow.user_id == user_id).values(**values),
            )
            await session.commit()
            if cursor.rowcount == 0:
                return None

        return await self.get(user_id, project_id)

    async def delete(self, user_id: str, project_id: str) -> bool:
        """Delete the project and cascade-delete its workspaces.

        Returns ``False`` if the project doesn't exist.
        """
        async with self._session_factory() as session:
            cursor = await session.execute(
                delete(ProjectRow).where(ProjectRow.id == project_id, ProjectRow.user_id == user_id),
            )
            await session.commit()
            return bool(cursor.rowcount)
