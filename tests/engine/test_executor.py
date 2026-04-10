"""Tests for the graph execution engine."""

from typing import Any

import pytest

from openfactcheck.engine import ExecutionResult, execute_pipeline

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal Blockly workspace JSON."""
    return {"blocks": {"blocks": list(blocks)}}


def _text_print(text: str, next_block: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a text_print block with a connected text literal."""
    block: dict[str, Any] = {
        "type": "text_print",
        "id": "print-1",
        "inputs": {
            "TEXT": {
                "block": {
                    "type": "text",
                    "id": "text-1",
                    "fields": {"TEXT": text},
                },
            },
        },
    }
    if next_block:
        block["next"] = {"block": next_block}
    return block


# ---------------------------------------------------------------------------
# execute_pipeline
# ---------------------------------------------------------------------------


async def test_execute_pipeline_empty() -> None:
    """execute_pipeline returns empty success for a pipeline with no blocks."""
    pipeline = _pipeline()

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == ""
    assert result.error is None


async def test_execute_pipeline_malformed() -> None:
    """execute_pipeline handles a completely wrong structure gracefully."""
    result = await execute_pipeline({"foo": "bar"})

    assert result.success is True
    assert result.output == ""


async def test_execute_pipeline_unknown_block_type() -> None:
    """execute_pipeline returns failure for an unregistered block type."""
    pipeline = _pipeline({"type": "nonexistent_block", "id": "bad-1"})

    result = await execute_pipeline(pipeline)

    assert result.success is False
    assert result.error is not None
    assert "nonexistent_block" in result.error


# ---------------------------------------------------------------------------
# text_print handler
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello World", "Hello World"),
        ("", ""),
        ("Line with spaces", "Line with spaces"),
    ],
)
async def test_execute_pipeline_text_print(text: str, expected: str) -> None:
    """text_print block outputs the connected text value."""
    pipeline = _pipeline(_text_print(text))

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == expected


async def test_execute_pipeline_text_print_no_input() -> None:
    """text_print with no TEXT input prints empty string."""
    pipeline = _pipeline({"type": "text_print", "id": "print-1", "inputs": {}})

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == ""


async def test_execute_pipeline_text_print_chained() -> None:
    """Two text_print blocks chained via next produce two output lines."""
    second: dict[str, Any] = {
        "type": "text_print",
        "id": "print-2",
        "inputs": {
            "TEXT": {
                "block": {
                    "type": "text",
                    "id": "text-2",
                    "fields": {"TEXT": "Goodbye"},
                },
            },
        },
    }
    pipeline = _pipeline(_text_print("Hello", next_block=second))

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == "Hello\nGoodbye"


async def test_execute_pipeline_multiple_top_level_blocks() -> None:
    """Multiple top-level blocks execute independently and produce ordered output."""
    pipeline = _pipeline(
        _text_print("First"),
        {
            "type": "text_print",
            "id": "print-2",
            "inputs": {
                "TEXT": {
                    "block": {
                        "type": "text",
                        "id": "text-2",
                        "fields": {"TEXT": "Second"},
                    },
                },
            },
        },
    )

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == "First\nSecond"


# ---------------------------------------------------------------------------
# Output truncation
# ---------------------------------------------------------------------------


async def test_execute_pipeline_output_truncation() -> None:
    """Output exceeding MAX_OUTPUT_BYTES is truncated with a single marker."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "text_print",
            "id": f"print-{i}",
            "inputs": {
                "TEXT": {
                    "block": {
                        "type": "text",
                        "id": f"text-{i}",
                        "fields": {"TEXT": "A" * 100},
                    },
                },
            },
        }
        for i in range(5000)
    ]
    pipeline = {"blocks": {"blocks": blocks}}

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output.count("[output truncated]") == 1


async def test_execute_pipeline_output_truncation_single_large_line() -> None:
    """A single line exceeding MAX_OUTPUT_BYTES triggers truncation."""
    pipeline = _pipeline(_text_print("X" * 100_000))

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == "[output truncated]"


# ---------------------------------------------------------------------------
# Null / malformed input handling
# ---------------------------------------------------------------------------


async def test_execute_pipeline_null_input_data() -> None:
    """text_print with null input data defaults gracefully."""
    pipeline = _pipeline({
        "type": "text_print",
        "id": "print-1",
        "inputs": {"TEXT": None},
    })

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == ""


async def test_execute_pipeline_null_connected_block() -> None:
    """text_print with explicit null block defaults gracefully."""
    pipeline = _pipeline({
        "type": "text_print",
        "id": "print-1",
        "inputs": {"TEXT": {"block": None}},
    })

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == ""


async def test_execute_pipeline_missing_inputs_key() -> None:
    """Block with no inputs key at all defaults gracefully."""
    pipeline = _pipeline({"type": "text_print", "id": "print-1"})

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == ""


async def test_execute_pipeline_null_next() -> None:
    """Block with null next doesn't crash."""
    pipeline = _pipeline({
        "type": "text_print",
        "id": "print-1",
        "inputs": {
            "TEXT": {
                "block": {"type": "text", "id": "t1", "fields": {"TEXT": "ok"}},
            },
        },
        "next": None,
    })

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == "ok"


# ---------------------------------------------------------------------------
# Nested inputs
# ---------------------------------------------------------------------------


async def test_execute_pipeline_nested_value_input() -> None:
    """A text block connected to another text block resolves correctly."""
    pipeline = _pipeline({
        "type": "text_print",
        "id": "print-1",
        "inputs": {
            "TEXT": {
                "block": {
                    "type": "text",
                    "id": "text-outer",
                    "fields": {"TEXT": "nested value"},
                },
            },
        },
    })

    result = await execute_pipeline(pipeline)

    assert result.success is True
    assert result.output == "nested value"


# ---------------------------------------------------------------------------
# Handler errors
# ---------------------------------------------------------------------------


async def test_execute_pipeline_handler_error() -> None:
    """EngineError from unknown block type is captured as failure."""
    pipeline = _pipeline({"type": "does_not_exist", "id": "bad-1"})

    result = await execute_pipeline(pipeline)

    assert result.success is False
    assert result.error is not None
    assert "does_not_exist" in result.error


# ---------------------------------------------------------------------------
# ExecutionResult
# ---------------------------------------------------------------------------


async def test_ExecutionResult_defaults() -> None:
    """ExecutionResult defaults error to None."""
    r = ExecutionResult(success=True, output="hello")

    assert r.success is True
    assert r.output == "hello"
    assert r.error is None
