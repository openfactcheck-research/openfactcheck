"""Secret request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from openfactcheck.api.models import Secret

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class SetSecretRequest(BaseModel):
    """Input payload for setting or replacing a secret's value."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    value: str = Field(min_length=1, max_length=4096)
    """The raw secret value. Stored encrypted and never returned.

    1 to 4096 characters.
    """


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class SecretResponse(BaseModel):
    """A stored secret returned in API responses, without its value."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str
    """Identifier for the secret, for example ``"openai"``."""

    hint: str
    """Trailing characters of the value, shown so the user can recognize the stored key."""

    created_at: datetime
    """Timestamp the secret was first set."""

    updated_at: datetime
    """Timestamp of the most recent change."""

    @staticmethod
    def from_model(secret: Secret) -> SecretResponse:
        """Convert a domain ``Secret`` to a response schema."""
        return SecretResponse(
            name=secret.name,
            hint=secret.hint,
            created_at=secret.created_at,
            updated_at=secret.updated_at,
        )
