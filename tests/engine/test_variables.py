"""Tests for variable block handlers."""

from __future__ import annotations

from typing import Any

import pytest

from openfactcheck.engine import execute_pipeline

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"blocks": {"blocks": list(blocks)}}


def _text(value: str) -> dict[str, Any]:
    return {"type": "text", "id": "t1", "fields": {"TEXT": value}}


def _num(value: float) -> dict[str, Any]:
    return {"type": "math_number", "id": "n1", "fields": {"NUM": str(value)}}


def _print(value_block: dict[str, Any]) -> dict[str, Any]:
    return {"type": "text_print", "id": "p1", "inputs": {"TEXT": {"block": value_block}}}


def _var_get(name: str) -> dict[str, Any]:
    return {"type": "variables_get", "id": "vg1", "fields": {"VAR": name}}


def _var_set(name: str, value_block: dict[str, Any], next_block: dict[str, Any] | None = None) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "variables_set",
        "id": "vs1",
        "fields": {"VAR": name},
        "inputs": {"VALUE": {"block": value_block}},
    }
    if next_block:
        block["next"] = {"block": next_block}
    return block


# ---------------------------------------------------------------------------
# variables_set + variables_get
# ---------------------------------------------------------------------------


async def test_set_and_get_string() -> None:
    chain = _var_set("msg", _text("hello"), next_block=_print(_var_get("msg")))
    result = await execute_pipeline(_pipeline(chain))
    assert result.output == "hello"


async def test_set_and_get_number() -> None:
    chain = _var_set("x", _num(42), next_block=_print(_var_get("x")))
    result = await execute_pipeline(_pipeline(chain))
    assert result.output == "42.0"


async def test_get_unset_variable_returns_empty() -> None:
    result = await execute_pipeline(_pipeline(_print(_var_get("missing"))))
    assert result.output == ""


async def test_overwrite_variable() -> None:
    chain = _var_set(
        "x",
        _text("first"),
        next_block=_var_set(
            "x",
            _text("second"),
            next_block=_print(_var_get("x")),
        ),
    )
    result = await execute_pipeline(_pipeline(chain))
    assert result.output == "second"


async def test_multiple_variables() -> None:
    chain = _var_set(
        "a",
        _text("hello"),
        next_block=_var_set(
            "b",
            _text(" world"),
            next_block={
                "type": "text_print",
                "id": "p1",
                "inputs": {
                    "TEXT": {
                        "block": {
                            "type": "text_join",
                            "id": "j1",
                            "inputs": {
                                "ADD0": {"block": _var_get("a")},
                                "ADD1": {"block": {"type": "variables_get", "id": "vg2", "fields": {"VAR": "b"}}},
                            },
                        }
                    }
                },
            },
        ),
    )
    result = await execute_pipeline(_pipeline(chain))
    assert result.output == "hello world"
