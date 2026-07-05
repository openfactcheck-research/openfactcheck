"""SQLite-backed user secret repository."""

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import Secret
from openfactcheck.api.repositories.constants import MAX_SECRETS_PER_USER
from openfactcheck.api.repositories.sqlite.helpers import row_to_dict
from openfactcheck.api.repositories.sqlite.tables import SecretRow


class SqliteSecretRepository:
    """SQLite-backed repository for a user's encrypted secrets."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Build a repository that opens sessions from the given factory.

        Args:
            session_factory: Async session factory bound to a SQLite engine.
        """
        self._session_factory = session_factory

    async def list(self, user_id: str, project_id: str | None = None) -> list[Secret]:
        """List the scope's secrets (masked), ordered by name."""
        scope = project_id or ""
        async with self._session_factory() as session:
            result = await session.execute(
                select(SecretRow)
                .where(SecretRow.user_id == user_id, SecretRow.project_id == scope)
                .order_by(SecretRow.name),
            )
            return [Secret.model_validate(row_to_dict(row)) for row in result.scalars()]

    async def set(
        self,
        user_id: str,
        name: str,
        ciphertext: str,
        hint: str,
        project_id: str | None = None,
    ) -> Secret | None:
        """Create or replace a secret's encrypted value within the scope.

        Returns ``None`` if storing a new secret would exceed
        [`MAX_SECRETS_PER_USER`][openfactcheck.api.repositories.constants.MAX_SECRETS_PER_USER]
        for that scope. Replacing an existing secret is always allowed.
        """
        scope = project_id or ""
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            row = await session.get(SecretRow, (user_id, scope, name))
            if row is None:
                count = await session.execute(
                    select(func.count())
                    .select_from(SecretRow)
                    .where(SecretRow.user_id == user_id, SecretRow.project_id == scope),
                )
                if count.scalar_one() >= MAX_SECRETS_PER_USER:
                    return None
                row = SecretRow(
                    user_id=user_id,
                    project_id=scope,
                    name=name,
                    ciphertext=ciphertext,
                    hint=hint,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.ciphertext = ciphertext
                row.hint = hint
                row.updated_at = now
            await session.commit()
            return Secret.model_validate(row_to_dict(row))

    async def get_ciphertext(self, user_id: str, name: str, project_id: str | None = None) -> str | None:
        """Return the stored ciphertext for a secret in the scope, or ``None`` if it is not set."""
        async with self._session_factory() as session:
            row = await session.get(SecretRow, (user_id, project_id or "", name))
            return row.ciphertext if row else None

    async def delete(self, user_id: str, name: str, project_id: str | None = None) -> bool:
        """Delete a secret from the scope. Returns ``False`` if it does not exist."""
        async with self._session_factory() as session:
            cursor = await session.execute(
                delete(SecretRow).where(
                    SecretRow.user_id == user_id,
                    SecretRow.project_id == (project_id or ""),
                    SecretRow.name == name,
                ),
            )
            await session.commit()
            return bool(cursor.rowcount)
