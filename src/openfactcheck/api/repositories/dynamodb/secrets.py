"""DynamoDB-backed user secret repository."""

import asyncio
from datetime import UTC, datetime

from openfactcheck.api.models import Secret
from openfactcheck.api.repositories.constants import MAX_SECRETS_PER_USER
from openfactcheck.api.repositories.dynamodb.base import BaseDynamoRepository
from openfactcheck.api.repositories.dynamodb.keys import secret_pk, secret_sk
from openfactcheck.api.repositories.dynamodb.types import DynamoItem


class DynamoSecretRepository(BaseDynamoRepository):
    """DynamoDB-backed repository for a user's encrypted secrets."""

    async def list(self, user_id: str) -> list[Secret]:
        """List the user's secrets (masked), ordered by name."""
        items = await self._query_by_pk(secret_pk(user_id), sk_prefix="SECRET#")
        secrets = [Secret.model_validate(item) for item in items]
        return sorted(secrets, key=lambda s: s.name)

    async def set(self, user_id: str, name: str, ciphertext: str, hint: str) -> Secret | None:
        """Create or replace a secret's encrypted value.

        Returns ``None`` if storing a new secret would exceed
        [`MAX_SECRETS_PER_USER`][openfactcheck.api.repositories.constants.MAX_SECRETS_PER_USER].
        Replacing an existing secret is always allowed.
        """
        existing = await self._query_by_pk(secret_pk(user_id), sk_prefix="SECRET#")
        names = {item.get("name") for item in existing}
        if name not in names and len(existing) >= MAX_SECRETS_PER_USER:
            return None

        now = datetime.now(UTC).isoformat()

        def _do() -> DynamoItem:
            response = self._table.update_item(
                Key={"PK": secret_pk(user_id), "SK": secret_sk(name)},
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

    async def get_ciphertext(self, user_id: str, name: str) -> str | None:
        """Return the stored ciphertext for a secret, or ``None`` if it is not set."""
        item = await self._get(secret_pk(user_id), secret_sk(name))
        if item is None:
            return None
        ciphertext = item.get("ciphertext")
        return ciphertext if isinstance(ciphertext, str) else None

    async def delete(self, user_id: str, name: str) -> bool:
        """Delete a secret. Returns ``False`` if it does not exist."""
        return await self._delete(secret_pk(user_id), secret_sk(name))
