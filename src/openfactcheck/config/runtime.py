"""Execution settings for a component's model calls.

A [`RuntimeSpec`][RuntimeSpec] holds timeout and retry settings, each optional so an unset field inherits the
chat layer's default. It merges field by field over a base spec and resolves to a chat
[`RuntimeConfig`][RuntimeConfig].
"""

from pydantic import BaseModel, ConfigDict

from openfactcheck.chat.config import RuntimeConfig


class RuntimeSpec(BaseModel):
    """Execution settings for a component's model calls.

    An unset field inherits the chat layer's runtime default.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    timeout: float | None = None
    """Per-request timeout in seconds."""

    max_retries: int | None = None
    """Automatic retries on transient transport failures."""

    max_parse_retries: int | None = None
    """Reprompts allowed when a structured-output reply fails validation."""

    def merged_over(self, base: "RuntimeSpec") -> "RuntimeSpec":
        """Return a spec where this spec's set fields override ``base``.

        Args:
            base: The lower-priority spec to fall back to per field.

        Returns:
            A spec combining both, preferring this spec's non-``None`` fields.
        """
        merged = base.model_dump()
        merged.update({key: value for key, value in self.model_dump().items() if value is not None})
        return RuntimeSpec(**merged)

    def to_runtime_config(self) -> RuntimeConfig:
        """Build the chat runtime configuration, letting unset fields take their defaults.

        Returns:
            The runtime configuration for this spec.
        """
        return RuntimeConfig(**{key: value for key, value in self.model_dump().items() if value is not None})
