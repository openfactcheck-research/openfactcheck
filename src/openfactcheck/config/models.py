"""The model selection for a component's calls.

A [`ModelSpec`][ModelSpec] captures a model choice as a ``"provider/model"`` name plus sampling parameters
and resolves it to the matching [`ModelConfig`][ModelConfig]. The first segment of the name is the provider
when it is a known one (openai, anthropic, openrouter); the remainder is the model id. Provider-specific
parameters are validated against the resolved provider, so a parameter the provider does not accept (for
example ``top_k`` on an OpenAI model) is rejected.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from openfactcheck.chat.config import ModelConfig
from openfactcheck.config.errors import ConfigError

_MODEL_CONFIG_ADAPTER: TypeAdapter[ModelConfig] = TypeAdapter(ModelConfig)


class ModelSpec(BaseModel):
    """A model selection and its sampling parameters, in ``"provider/model"`` form.

    Provider-specific parameters are validated against the resolved provider when the spec is turned into a
    chat configuration, so a parameter the provider does not accept (for example ``top_k`` on an OpenAI model)
    is rejected then.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    name: str | None = None
    """Model name as ``"provider/model"`` (for example ``"anthropic/claude-sonnet-4-6"``).

    When unset, the surrounding configuration supplies a fallback.
    """

    temperature: float | None = None
    """How random the model's output is. Lower is more focused, higher more varied."""

    max_output_tokens: int | None = None
    """Cap on the tokens the model may generate in its response."""

    top_p: float | None = None
    """Nucleus sampling cutoff."""

    seed: int | None = None
    """Request reproducible sampling, for OpenAI-compatible providers."""

    frequency_penalty: float | None = None
    """Penalize tokens by how often they have appeared, for OpenAI-compatible providers."""

    presence_penalty: float | None = None
    """Penalize tokens that have appeared at all, for OpenAI-compatible providers."""

    reasoning_effort: Literal["low", "medium", "high"] | None = None
    """Reasoning budget hint, for OpenAI-compatible providers."""

    top_k: int | None = None
    """Sample from the top-k tokens at each step, for Anthropic."""

    thinking: bool | None = None
    """Enable Anthropic extended thinking. Requires [`thinking_budget_tokens`][ModelSpec.thinking_budget_tokens]."""

    thinking_budget_tokens: int | None = None
    """Tokens Anthropic may spend on the reasoning trace when thinking is on."""

    def to_model_config(self, *, fallback_name: str | None = None) -> ModelConfig:
        """Build the provider configuration for this spec.

        The name is taken from [`name`][ModelSpec.name], falling back to ``fallback_name``; its first segment
        is the provider when it is a known one (openai, anthropic, openrouter), and the remainder is the model
        id. The set sampling parameters are then validated against the resolved provider.

        Args:
            fallback_name: Model name to use when [`name`][ModelSpec.name] is unset.

        Returns:
            The provider configuration for the resolved model name and the set sampling parameters.

        Raises:
            ConfigError: If no name is set or supplied, or a parameter does not belong to the resolved
                provider or fails its constraints. The message names the model, the provider, and each
                offending parameter.
        """
        resolved = (self.name or fallback_name or "").strip()
        if not resolved:
            raise ConfigError("no model name; set the spec's name or pass a fallback.")
        match resolved.partition("/"):
            case ("openai" | "anthropic" | "openrouter") as provider, "/", model if model:
                base = {"provider": provider, "model": model}
            case _:
                base = {"provider": "openai", "model": resolved}
        params = {key: value for key, value in self.model_dump(exclude={"name"}).items() if value is not None}
        try:
            return _MODEL_CONFIG_ADAPTER.validate_python({**base, **params})
        except ValidationError as exc:
            provider, model = base["provider"], base["model"]
            issues: list[str] = []
            for error in exc.errors():
                # The discriminated union prefixes each path with the provider tag; drop it, it is already named.
                loc = error["loc"][1:] if error["loc"][:1] == (provider,) else error["loc"]
                field = ".".join(str(part) for part in loc) or "value"
                issues.append(f"{field}: {error['msg']}")
            raise ConfigError(
                f"invalid configuration for model '{model}' (provider '{provider}'): {'; '.join(issues)}."
            ) from exc
