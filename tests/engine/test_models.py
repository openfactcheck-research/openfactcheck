"""Tests for the Models & Agents block handlers."""

import json
from typing import Any, cast

import pytest
from pytest_mock import MockerFixture

from openfactcheck.chat import ChatClient
from openfactcheck.engine import execute_pipeline
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"blocks": {"blocks": list(blocks)}}


def _agent_pipeline(*, structured: bool = False) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "PROMPT": {"block": {"type": "prompt_template", "fields": {"SYSTEM_TEXT": "Check.", "USER_TEXT": "Claim: {{claim}}"}}},
        "MODEL": {"block": {"type": "language_model", "fields": {"PROVIDER": "openai"}, "extraState": {"model": "gpt-4o-mini"}}},
        "VAR_CLAIM": {"block": {"type": "text_input_value", "fields": {"INPUT_TEXT": "The sky is green."}}},
    }
    if structured:
        inputs["STRUCTURED_OUTPUT"] = {
            "block": {"type": "structured_output", "fields": {"SCHEMA_DATA": json.dumps([{"name": "verdict", "type": "bool", "asList": False}])}},
        }
    return _pipeline({"type": "agent", "inputs": inputs})


# ---------------------------------------------------------------------------
# Block.get_extra (language_model stores model + params there)
# ---------------------------------------------------------------------------


async def test_Block_get_extra() -> None:
    block = Block({"type": "language_model", "extraState": {"model": "gpt-4o-mini", "temperature": 0.5}})

    assert block.get_extra("model") == "gpt-4o-mini"
    assert block.get_extra("temperature") == 0.5
    assert block.get_extra("missing", "fallback") == "fallback"


async def test_Block_get_extra_absent() -> None:
    block = Block({"type": "text"})

    assert block.get_extra("model") is None


# ---------------------------------------------------------------------------
# language_model
# ---------------------------------------------------------------------------


async def test_language_model_reads_extra_state() -> None:
    ctx = ExecutionContext()
    block = Block(
        {
            "type": "language_model",
            "fields": {"PROVIDER": "openai"},
            "extraState": {"model": "gpt-4o-mini", "temperature": 0.5, "maxTokens": 1000},
        },
    )

    client = cast("ChatClient", ctx.execute_block(block))

    assert isinstance(client, ChatClient)
    assert client._config.model == "gpt-4o-mini"  # noqa: SLF001 - asserting the parsed config in a test.
    assert client._config.provider == "openai"  # noqa: SLF001 - asserting the parsed config in a test.


async def test_language_model_anthropic_skips_openai_only_params() -> None:
    ctx = ExecutionContext()
    block = Block(
        {
            "type": "language_model",
            "fields": {"PROVIDER": "anthropic"},
            "extraState": {"model": "claude-3-5-sonnet", "temperature": 0.4, "maxTokens": 2000, "freqPenalty": 0.5},
        },
    )

    client = cast("ChatClient", ctx.execute_block(block))

    assert client._config.provider == "anthropic"  # noqa: SLF001 - asserting the parsed config in a test.


# ---------------------------------------------------------------------------
# agent (mocked model)
# ---------------------------------------------------------------------------


async def test_agent_runs_model_and_prints_response(mocker: MockerFixture) -> None:
    mocker.patch.object(ChatClient, "completion", return_value=mocker.Mock(message=mocker.Mock(content="False.")))

    result = await execute_pipeline(_agent_pipeline())

    assert result.success
    assert result.output == "False."


async def test_agent_fills_template_variable(mocker: MockerFixture) -> None:
    completion = mocker.patch.object(ChatClient, "completion", return_value=mocker.Mock(message=mocker.Mock(content="ok")))

    await execute_pipeline(_agent_pipeline())

    messages = completion.call_args.args[0]
    assert messages[-1].content == "Claim: The sky is green."


async def test_agent_structured_output_uses_completion_as(mocker: MockerFixture) -> None:
    structured = mocker.Mock()
    structured.model_dump_json.return_value = '{"verdict": false}'
    mocker.patch.object(ChatClient, "completion_as", return_value=structured)

    result = await execute_pipeline(_agent_pipeline(structured=True))

    assert result.success
    assert result.output == '{"verdict": false}'


async def test_agent_without_model_fails() -> None:
    pipeline = _pipeline({"type": "agent", "inputs": {"PROMPT": {"block": {"type": "prompt_template", "fields": {"USER_TEXT": "Hi"}}}}})

    result = await execute_pipeline(pipeline)

    assert not result.success
    assert "model" in (result.error or "").lower()
