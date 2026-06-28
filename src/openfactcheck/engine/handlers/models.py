"""Handlers for the Models & Agents blocks: language model and agent.

The language-model block builds a [`ChatClient`][openfactcheck.chat.ChatClient];
the agent fills the connected prompt template and runs it through the model.
Provider API keys are read from the environment, which the runner populates from
the user's stored secrets.
"""

from typing import TYPE_CHECKING, cast

from pydantic import BaseModel

from openfactcheck.chat import AnthropicConfig, ChatClient, OpenAIConfig, OpenRouterConfig
from openfactcheck.chat.errors import ChatModelError
from openfactcheck.engine import resolve
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.errors import EngineError
from openfactcheck.engine.handler import handler

if TYPE_CHECKING:
    from openfactcheck.chat.config import ModelConfig
    from openfactcheck.prompts import PromptTemplate

# Provider id to its chat-layer config class.
_CONFIG_CLASS: dict[str, type[BaseModel]] = {
    "openai": OpenAIConfig,
    "anthropic": AnthropicConfig,
    "openrouter": OpenRouterConfig,
}


@handler("language_model")
def language_model(block: Block, _ctx: ExecutionContext) -> ChatClient:
    """Build a chat client from the block's provider, model, and parameters.

    The model name and sampling parameters live in the block's ``extraState``.
    The provider's API key is read from the environment when the client runs.
    """
    provider = block.get_field("PROVIDER", default="openai")
    kwargs: dict[str, object] = {"model": _opt_str(block, "model") or ""}
    _set(kwargs, "temperature", _opt_float(block, "temperature"))
    _set(kwargs, "top_p", _opt_float(block, "topP"))
    _set(kwargs, "max_output_tokens", _opt_int(block, "maxTokens"))
    if provider in {"openai", "openrouter"}:
        _set(kwargs, "frequency_penalty", _opt_float(block, "freqPenalty"))
        _set(kwargs, "presence_penalty", _opt_float(block, "presPenalty"))
        _set(kwargs, "reasoning_effort", _opt_str(block, "reasoningEffort"))

    config_class = _CONFIG_CLASS.get(provider, OpenAIConfig)
    return ChatClient(config=cast("ModelConfig", config_class(**kwargs)))


@handler("agent")
def agent(block: Block, ctx: ExecutionContext) -> object:
    """Fill the connected template and run it through the connected model.

    With a structured-output block attached, the reply is constrained to that
    model and printed as JSON; otherwise the model's free text is printed.
    """
    prompt_block = block.get_input_block("PROMPT")
    model_block = block.get_input_block("MODEL")
    if prompt_block is None or model_block is None:
        raise EngineError("Agent needs both a prompt and a model.")

    template = cast("PromptTemplate", ctx.execute_block(prompt_block))
    values = {name: resolve.string(block, ctx, f"VAR_{name.upper()}") for name in template.variables}
    messages = template.to_messages(**values)
    output_block = block.get_input_block("STRUCTURED_OUTPUT")

    try:
        client = cast("ChatClient", ctx.execute_block(model_block))
        if output_block is not None:
            schema = cast("type[BaseModel]", ctx.execute_block(output_block))
            structured = client.completion_as(messages, schema)
            result, rendered = structured, structured.model_dump_json(indent=2)
        else:
            response = client.completion(messages)
            result, rendered = response, response.message.content
    except ChatModelError as e:
        raise EngineError(f"Model call failed: {e}") from e

    ctx.print(rendered)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set(kwargs: dict[str, object], key: str, value: object) -> None:
    """Add ``key`` to ``kwargs`` only when ``value`` is present."""
    if value is not None:
        kwargs[key] = value


def _opt_float(block: Block, key: str) -> float | None:
    value = block.get_extra(key)
    return float(value) if isinstance(value, (int, float)) else None


def _opt_int(block: Block, key: str) -> int | None:
    value = block.get_extra(key)
    return int(value) if isinstance(value, (int, float)) else None


def _opt_str(block: Block, key: str) -> str | None:
    value = block.get_extra(key)
    return value if isinstance(value, str) else None
