"""Configuration for Serper-backed web retrieval.

A [`SerperSpec`][SerperSpec] groups the settings for the Serper search service and builds a configured
[`SerperClient`][SerperClient]. It lives with the integration so each external service owns its own
configuration, keeping the generic run configuration free of service-specific fields.
"""

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from openfactcheck.integrations.serper.client import DEFAULT_TIMEOUT, SerperClient


class SerperSpec(BaseModel):
    """Settings for the Serper web-search service.

    An unset field takes the client's default. The API key falls back to the one supplied at build time, then
    to the ``SERPER_API_KEY`` environment variable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    api_key: SecretStr | None = None
    """Serper API key, overriding the fallback supplied at build time."""

    gl: str | None = None
    """Country code applied to searches (for example ``"us"``)."""

    hl: str | None = None
    """Language code applied to searches (for example ``"en"``)."""

    timeout: float | None = Field(default=None, gt=0)
    """Per-request timeout in seconds.

    Must be positive.
    """

    def to_client(self, *, fallback_api_key: SecretStr | None = None) -> SerperClient:
        """Build a Serper client from this spec.

        Args:
            fallback_api_key: API key to use when this spec sets none; an empty value defers to the
                ``SERPER_API_KEY`` environment variable.

        Returns:
            A Serper client for the resolved key, locale, and timeout.
        """
        key = self.api_key if self.api_key is not None else fallback_api_key
        api_key = key.get_secret_value() if key is not None else None
        return SerperClient(
            api_key=api_key or None,
            gl=self.gl,
            hl=self.hl,
            timeout=self.timeout if self.timeout is not None else DEFAULT_TIMEOUT,
        )
