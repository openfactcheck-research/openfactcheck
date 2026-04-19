"""Model and runtime configuration for the chat layer.

Build a provider-specific configuration (for example
[`OpenAIConfig`][OpenAIConfig]), optionally pair it with a
[`RuntimeConfig`][RuntimeConfig] for execution-level settings, and pass
both to [`ChatClient`][ChatClient].

[`ModelConfig`][ModelConfig] is the union of every provider configuration;
callers that must work with any provider accept a ``ModelConfig`` and
branch on ``config.provider``.

Example:
    ```python
    from openfactcheck.chat import ChatClient, OpenAIConfig, UserMessage

    client = ChatClient(config=OpenAIConfig(model="gpt-4o", temperature=0.2))
    response = client.completion([UserMessage(content="Hello")])
    ```
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Discriminator, Field, model_validator

type ProviderName = Literal["openai", "anthropic"]
"""Identifier for a chat provider."""


# ---------------------------------------------------------------------------
# Base config (not exported, not directly instantiated)
# ---------------------------------------------------------------------------


class BaseModelConfig(BaseModel):
    """Common parameters shared across every provider config.

    Not instantiated directly; use a provider-specific subclass.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_attribute_docstrings=True,
    )

    model: str
    """Identifier of the model to call, for example ``"gpt-4o"``."""

    temperature: float | None = None
    """How random the model's output is. Lower values are more focused, higher values more varied."""

    max_output_tokens: int | None = Field(default=None, gt=0)
    """Cap on the number of tokens the model may generate in its response.

    Must be positive.
    """

    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    """Nucleus sampling cutoff.

    Range ``[0.0, 1.0]``.
    """


# ---------------------------------------------------------------------------
# Provider-specific configs
# ---------------------------------------------------------------------------


class OpenAIConfig(BaseModelConfig):
    """Configuration for an OpenAI model.

    Example:
        ```python
        config = OpenAIConfig(
            model="gpt-4o",
            temperature=0.2,
            max_output_tokens=500,
        )
        ```
    """

    provider: Literal["openai"] = "openai"
    """Identifies this configuration as OpenAI's."""

    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    """How random the model's output is. Lower is more focused, higher more varied.

    Range ``[0.0, 2.0]``.
    """

    seed: int | None = None
    """Request reproducible sampling. Determinism is best-effort, not guaranteed."""

    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    """Penalize tokens by how often they have already appeared. Positive values reduce repetition.

    Range ``[-2.0, 2.0]``.
    """

    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    """Penalize tokens that have already appeared at all. Positive values encourage novelty.

    Range ``[-2.0, 2.0]``.
    """

    reasoning_effort: Literal["low", "medium", "high"] | None = None
    """Reasoning budget hint. Ignored by non-reasoning models."""


class AnthropicConfig(BaseModelConfig):
    """Configuration for an Anthropic model.

    Example:
        ```python
        config = AnthropicConfig(
            model="claude-sonnet-4-6",
            temperature=0.4,
            thinking=True,
            thinking_budget_tokens=4000,
        )
        ```
    """

    provider: Literal["anthropic"] = "anthropic"
    """Identifies this configuration as Anthropic's."""

    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    """How random the model's output is. Lower is more focused, higher more varied.

    Range ``[0.0, 1.0]``.
    """

    top_k: int | None = Field(default=None, gt=0)
    """Sample from the top-k tokens at each step.

    Must be positive.
    """

    thinking: bool = False
    """Enable extended thinking so the model can show its reasoning before answering."""

    thinking_budget_tokens: int | None = Field(default=None, gt=0)
    """How many tokens the model may spend on the reasoning trace.

    Only set when ``thinking=True``. Must be positive.
    """

    @model_validator(mode="after")
    def _check_thinking_coupling(self) -> Self:
        """Enforce the thinking/budget coupling: budget is required iff thinking is on.

        Returns:
            The validated config, unchanged.

        Raises:
            ValueError: If ``thinking=True`` without a budget, or if a
                budget is supplied while ``thinking=False``.
        """
        if self.thinking and self.thinking_budget_tokens is None:
            raise ValueError("thinking_budget_tokens is required when thinking=True.")
        if not self.thinking and self.thinking_budget_tokens is not None:
            raise ValueError("thinking_budget_tokens must not be set when thinking=False.")
        return self


# ---------------------------------------------------------------------------
# Union + runtime
# ---------------------------------------------------------------------------


type ModelConfig = Annotated[OpenAIConfig | AnthropicConfig, Discriminator("provider")]
"""Union of every provider configuration.

Accept this type in code that must work with any provider; branch on
``config.provider`` to distinguish the concrete subclass.
"""


class RuntimeConfig(BaseModel):
    """Execution-level settings for a chat request.

    Example:
        ```python
        runtime = RuntimeConfig(timeout=30.0, max_retries=5)
        ```
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_attribute_docstrings=True,
    )

    timeout: float | None = Field(default=None, gt=0)
    """Per-request timeout in seconds.

    Must be positive. Unset uses the SDK default.
    """

    max_retries: int = Field(default=2, ge=0)
    """Automatic retries on transient failures.

    Set to ``0`` to disable. Must be non-negative.
    """
