"""DynamoDB-backed user secret repository."""

import asyncio
from datetime import UTC, datetime

from openfactcheck.api.models import Secret
from openfactcheck.api.repositories.constants import MAX_SECRETS_PER_USER
from openfactcheck.api.repositories.dynamodb.base import BaseDynamoRepository
from openfactcheck.api.repositories.dynamodb.keys import project_secret_pk, secret_pk, secret_sk
from openfactcheck.api.repositories.dynamodb.types import DynamoItem


class DynamoSecretRepository(BaseDynamoRepository):
    """DynamoDB-backed repository for a user's encrypted secrets."""

    @staticmethod
    def _pk(user_id: str, project_id: str | None) -> str:
        """Partition key for the scope: the user's globals, or a project's overrides."""
        return project_secret_pk(user_id, project_id) if project_id else secret_pk(user_id)

    async def list(self, user_id: str, project_id: str | None = None) -> list[Secret]:
        """List the scope's secrets (masked), ordered by name."""
        items = await self._query_by_pk(self._pk(user_id, project_id), sk_prefix="SECRET#")
        secrets = [Secret.model_validate(item) for item in items]
        return sorted(secrets, key=lambda s: s.name)

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
        pk = self._pk(user_id, project_id)
        existing = await self._query_by_pk(pk, sk_prefix="SECRET#")
        names = {item.get("name") for item in existing}
        if name not in names and len(existing) >= MAX_SECRETS_PER_USER:
            return None

        now = datetime.now(UTC).isoformat()

        def _do() -> DynamoItem:
            response = self._table.update_item(
                Key={"PK": pk, "SK": secret_sk(name)},
                UpdateExpression=(
                    "SET #name = :name, hint = :hint, ciphertext = :ciphertext, "
                    "updatedAt = :now, createdAt = if_not_exists(createdAt, :now)"
                ),
                ExpressionAttributeNames={"#name": "name"},
                ExpressionAttributeValues={
                    ":name": name,
                    ":hint": hint,
                    ":ciphertext": ciphertext,
                    ":now": now,
                },
                ReturnValues="ALL_NEW",
            )
            return response["Attributes"]

        attrs = await asyncio.to_thread(_do)
        return Secret.model_validate(attrs)

    async def get_ciphertext(self, user_id: str, name: str, project_id: str | None = None) -> str | None:
        """Return the stored ciphertext for a secret in the scope, or ``None`` if it is not set."""
        item = await self._get(self._pk(user_id, project_id), secret_sk(name))
        if item is None:
            return None
        ciphertext = item.get("ciphertext")
        return ciphertext if isinstance(ciphertext, str) else None

    async def delete(self, user_id: str, name: str, project_id: str | None = None) -> bool:
        """Delete a secret from the scope. Returns ``False`` if it does not exist."""
        return await self._delete(self._pk(user_id, project_id), secret_sk(name))
