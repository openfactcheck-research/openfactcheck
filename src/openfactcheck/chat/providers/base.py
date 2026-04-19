"""Protocol for chat provider definitions.

A provider encapsulates provider-level concerns (capability declaration and
per-provider configuration validation) so the rest of the chat layer can
dispatch on ``config.provider`` without knowing the concrete type.

Subclass [`BaseProvider`][BaseProvider] to add support for a new provider,
then register the subclass in ``openfactcheck.chat.providers``.

Example:
    ```python
    from openfactcheck.chat.config import ModelConfig
    from openfactcheck.chat.errors import ProviderError
    from openfactcheck.chat.providers.base import BaseProvider, ProviderCapabilities


    class FakeProvider(BaseProvider):
        name = "fake"
        capabilities = ProviderCapabilities(streaming=True)

        def validate_config(self, config: ModelConfig) -> None:
            if not config.model.startswith("fake/"):
                raise ProviderError(f"Unexpected model id: {config.model}")
    ```
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from openfactcheck.chat.config import ModelConfig


class ProviderCapabilities(BaseModel):
    """Provider-level capability flags.

    Every flag defaults to ``False``; each provider implementation must
    explicitly declare what it supports. Values describe provider defaults,
    not per-model guarantees.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    streaming: bool = False
    """Whether the provider supports streaming responses."""

    tool_calling: bool = False
    """Whether the provider supports tool calls as part of a response."""

    structured_output: bool = False
    """Whether the provider supports constrained (schema-bound) output."""


class BaseProvider(ABC):
    """Abstract provider definition.

    Concrete subclasses declare the provider's
    [`name`][BaseProvider.name] and
    [`capabilities`][BaseProvider.capabilities], and implement
    [`validate_config`][BaseProvider.validate_config] to check
    provider-specific configuration rules.
    """

    name: str
    """Stable identifier matched against ``config.provider`` to dispatch to this provider."""

    capabilities: ProviderCapabilities
    """Capability flags for this provider."""

    @abstractmethod
    def validate_config(self, config: ModelConfig) -> None:
        """Raise if ``config`` is invalid for this provider.

        Implementations narrow the config type and check provider-specific
        semantic constraints, for example temperature ranges for reasoning
        models or required fields the provider enforces at the API level.

        Args:
            config: Provider configuration to validate.

        Raises:
            ProviderError: If the configuration is invalid for this
                provider.
        """
