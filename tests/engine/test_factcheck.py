"""Tests for the Fact-Checking block handler."""

from typing import Any

import pytest
from pytest_mock import MockerFixture

from openfactcheck import OpenFactCheck
from openfactcheck.components.types import Claim, Result, Verdict
from openfactcheck.engine import execute_pipeline

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"blocks": {"blocks": list(blocks)}}


def _factcheck_pipeline(*, pipeline: str = "factool", with_input: bool = True, with_model: bool = True) -> dict[str, Any]:
    check: dict[str, Any] = {"type": "openfactcheck", "fields": {"PIPELINE": pipeline}}
    if with_model:
        check["inputs"] = {
            "MODEL": {
                "block": {"type": "language_model", "fields": {"PROVIDER": "openai"}, "extraState": {"model": "gpt-4o-mini"}},
            },
        }
    if not with_input:
        return _pipeline(check)
    return _pipeline(
        {
            "type": "text_input",
            "fields": {"INPUT_TEXT": "The Eiffel Tower opened in 1889."},
            "next": {"block": check},
        },
    )


def _result() -> Result:
    verdict = Verdict(claim=Claim(text="The Eiffel Tower opened in 1889."), label="supported", reasoning="ok")
    return Result(verdicts=[verdict])


async def test_openfactcheck_runs_pipeline_over_the_input(mocker: MockerFixture) -> None:
    """The handler runs the configured pipeline over ``input_text`` and prints the result."""
    run = mocker.patch.object(OpenFactCheck, "run", return_value=_result())

    result = await execute_pipeline(_factcheck_pipeline())

    assert result.success
    assert '"supported"' in result.output
    assert run.call_args.args[0] == "The Eiffel Tower opened in 1889."


async def test_openfactcheck_without_input_fails() -> None:
    """With no Input Text block above, the run fails with a clear message."""
    result = await execute_pipeline(_factcheck_pipeline(with_input=False))

    assert not result.success
    assert "input text" in (result.error or "").lower()


async def test_openfactcheck_without_model_uses_pipeline_default(mocker: MockerFixture) -> None:
    """With no language model connected, the pipeline runs on its own default model."""
    run = mocker.patch.object(OpenFactCheck, "run", return_value=_result())

    result = await execute_pipeline(_factcheck_pipeline(with_model=False))

    assert result.success
    assert run.called


async def test_openfactcheck_carries_the_model_sampling_into_the_config(mocker: MockerFixture) -> None:
    """A connected language model's name and sampling parameters reach the run configuration."""
    checker = mocker.patch("openfactcheck.OpenFactCheck")
    checker.return_value.run.return_value = _result()
    model = {
        "type": "language_model",
        "fields": {"PROVIDER": "openai"},
        "extraState": {"model": "gpt-4o", "temperature": 0.2, "topP": 0.9, "maxTokens": 256, "freqPenalty": 0.1},
    }
    check = {"type": "openfactcheck", "fields": {"PIPELINE": "factcheckgpt"}, "inputs": {"MODEL": {"block": model}}}
    pipeline = _pipeline(
        {"type": "text_input", "fields": {"INPUT_TEXT": "The Eiffel Tower opened in 1889."}, "next": {"block": check}},
    )

    result = await execute_pipeline(pipeline)

    assert result.success
    config = checker.call_args.args[0]
    assert config.model.name == "openai/gpt-4o"
    assert config.model.temperature == 0.2
    assert config.model.top_p == 0.9
    assert config.model.max_output_tokens == 256
    assert config.model.frequency_penalty == 0.1


async def test_openfactcheck_drops_openai_only_params_for_anthropic(mocker: MockerFixture) -> None:
    """Penalties the block serialises for a temperature-capable Anthropic model are not passed through."""
    checker = mocker.patch("openfactcheck.OpenFactCheck")
    checker.return_value.run.return_value = _result()
    model = {
        "type": "language_model",
        "fields": {"PROVIDER": "anthropic"},
        "extraState": {"model": "claude-sonnet-4-6", "temperature": 0.3, "freqPenalty": 0.5, "presPenalty": 0.5},
    }
    check = {"type": "openfactcheck", "fields": {"PIPELINE": "factcheckgpt"}, "inputs": {"MODEL": {"block": model}}}
    pipeline = _pipeline(
        {"type": "text_input", "fields": {"INPUT_TEXT": "The Eiffel Tower opened in 1889."}, "next": {"block": check}},
    )

    result = await execute_pipeline(pipeline)

    assert result.success
    config = checker.call_args.args[0]
    assert config.model.name == "anthropic/claude-sonnet-4-6"
    assert config.model.temperature == 0.3
    assert config.model.frequency_penalty is None
    assert config.model.presence_penalty is None
