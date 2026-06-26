"""DynamoDB-backed user preferences repository."""

from openfactcheck.api.models import Preferences
from openfactcheck.api.repositories.dynamodb.base import BaseDynamoRepository
from openfactcheck.api.repositories.dynamodb.keys import preferences_pk, preferences_sk
from openfactcheck.api.repositories.dynamodb.types import DynamoItem


class DynamoPreferencesRepository(BaseDynamoRepository):
    """DynamoDB-backed repository for a user's preferences."""

    async def get(self, user_id: str) -> Preferences:
        """Return the user's preferences, or an all-default record if none are stored."""
        item = await self._get(preferences_pk(user_id), preferences_sk())
        return Preferences.model_validate(item) if item else Preferences()

    async def set(self, user_id: str, preferences: Preferences) -> Preferences:
        """Replace the user's preferences with the given record."""
        item: DynamoItem = {
            "PK": preferences_pk(user_id),
            "SK": preferences_sk(),
            **preferences.model_dump(by_alias=True),
        }
        await self._put(item)
        return preferences
