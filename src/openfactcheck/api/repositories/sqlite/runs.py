"""SQLite implementation of the run repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import Run, RunCreate, RunStatus
from openfactcheck.api.repositories.constants import generate_id
from openfactcheck.api.repositories.sqlite.helpers import ensure_utc, ensure_utc_optional
from openfactcheck.api.repositories.sqlite.tables import RunRow


def _row_to_model(row: RunRow) -> Run:
    return Run(
        id=row.id,
        user_id=row.user_id,
        project_id=row.project_id,
        workspace_id=row.workspace_id,
        status=RunStatus(row.status),
        pipeline=json.loads(row.pipeline_json),
        output=row.output,
        error=row.error,
        started_at=ensure_utc_optional(row.started_at),
        completed_at=ensure_utc_optional(row.completed_at),
        created_at=ensure_utc(row.created_at),
        updated_at=ensure_utc(row.updated_at),
    )


class SqliteRunRepository:
    """Run CRUD backed by SQLite via SQLAlchemy async."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, user_id: str, project_id: str, data: RunCreate) -> Run:
        now = datetime.now(UTC)
        row = RunRow(
            id=generate_id(),
            user_id=user_id,
            project_id=project_id,
            workspace_id=data.workspace_id,
            status=RunStatus.PENDING,
            pipeline_json=json.dumps(data.pipeline),
            created_at=now,
            updated_at=now,
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
        return _row_to_model(row)

    async def get(self, user_id: str, project_id: str, run_id: str) -> Run | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(RunRow).where(
                    RunRow.id == run_id,
                    RunRow.user_id == user_id,
                    RunRow.project_id == project_id,
                )
            )
            row = result.scalar_one_or_none()
            return _row_to_model(row) if row else None

    async def update_status(
        self,
        user_id: str,
        project_id: str,
        run_id: str,
        status: RunStatus,
        output: str | None = None,
        error: str | None = None,
    ) -> Run | None:
        now = datetime.now(UTC)
        values: dict[str, object] = {"status": status.value, "updated_at": now}

        if status == RunStatus.RUNNING:
            values["started_at"] = now
        if status in (RunStatus.COMPLETED, RunStatus.FAILED):
            values["completed_at"] = now
        if output is not None:
            values["output"] = output
        if error is not None:
            values["error"] = error

        async with self._session_factory() as session:
            cursor = await session.execute(
                update(RunRow)
                .where(
                    RunRow.id == run_id,
                    RunRow.user_id == user_id,
                    RunRow.project_id == project_id,
                )
                .values(**values)
            )
            await session.commit()
            if cursor.rowcount == 0:  # type: ignore[union-attr]
                return None

        return await self.get(user_id, project_id, run_id)

    async def list_by_project(
        self,
        user_id: str,
        project_id: str,
        workspace_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Run]:
        async with self._session_factory() as session:
            stmt = (
                select(RunRow)
                .where(RunRow.user_id == user_id, RunRow.project_id == project_id)
                .order_by(RunRow.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            if workspace_id is not None:
                stmt = stmt.where(RunRow.workspace_id == workspace_id)
            result = await session.execute(stmt)
            return [_row_to_model(row) for row in result.scalars()]
