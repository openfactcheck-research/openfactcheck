"""Tests for text block handlers."""

from __future__ import annotations

from typing import Any

import pytest

from openfactcheck.engine import execute_pipeline

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"blocks": {"blocks": list(blocks)}}


def _text(value: str) -> dict[str, Any]:
    return {"type": "text", "id": "t1", "fields": {"TEXT": value}}


def _print(value_block: dict[str, Any], next_block: dict[str, Any] | None = None) -> dict[str, Any]:
    block: dict[str, Any] = {"type": "text_print", "id": "p1", "inputs": {"TEXT": {"block": value_block}}}
    if next_block:
        block["next"] = {"block": next_block}
    return block


# ---------------------------------------------------------------------------
# text_join
# ---------------------------------------------------------------------------


async def test_text_join() -> None:
    block = {
        "type": "text_join",
        "id": "j1",
        "inputs": {
            "ADD0": {"block": _text("Hello")},
            "ADD1": {"block": _text(" ")},
            "ADD2": {"block": _text("World")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "Hello World"


async def test_text_join_empty() -> None:
    block = {"type": "text_join", "id": "j1", "inputs": {}}
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == ""


# ---------------------------------------------------------------------------
# text_append
# ---------------------------------------------------------------------------


async def test_text_append() -> None:
    set_var: dict[str, Any] = {
        "type": "text_append",
        "id": "a1",
        "fields": {"VAR": "msg"},
        "inputs": {"TEXT": {"block": _text("Hello")}},
        "next": {
            "block": {
                "type": "text_append",
                "id": "a2",
                "fields": {"VAR": "msg"},
                "inputs": {"TEXT": {"block": _text(" World")}},
                "next": {
                    "block": {
                        "type": "text_print",
                        "id": "p1",
                        "inputs": {
                            "TEXT": {
                                "block": {
                                    "type": "variables_get",
                                    "id": "vg1",
                                    "fields": {"VAR": "msg"},
                                }
                            }
                        },
                    }
                },
            }
        },
    }
    result = await execute_pipeline(_pipeline(set_var))
    assert result.output == "Hello World"


# ---------------------------------------------------------------------------
# text_length
# ---------------------------------------------------------------------------


async def test_text_length() -> None:
    block = {
        "type": "text_length",
        "id": "l1",
        "inputs": {"VALUE": {"block": _text("Hello")}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "5"


async def test_text_length_empty() -> None:
    block = {
        "type": "text_length",
        "id": "l1",
        "inputs": {"VALUE": {"block": _text("")}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "0"


# ---------------------------------------------------------------------------
# text_isEmpty
# ---------------------------------------------------------------------------


async def test_text_is_empty_true() -> None:
    block = {
        "type": "text_isEmpty",
        "id": "e1",
        "inputs": {"VALUE": {"block": _text("")}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "True"


async def test_text_is_empty_false() -> None:
    block = {
        "type": "text_isEmpty",
        "id": "e1",
        "inputs": {"VALUE": {"block": _text("hi")}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "False"


# ---------------------------------------------------------------------------
# text_indexOf
# ---------------------------------------------------------------------------


async def test_text_index_of_first() -> None:
    block = {
        "type": "text_indexOf",
        "id": "idx1",
        "fields": {"END": "FIRST"},
        "inputs": {
            "VALUE": {"block": _text("abcabc")},
            "FIND": {"block": _text("bc")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "2"  # 1-based


async def test_text_index_of_last() -> None:
    block = {
        "type": "text_indexOf",
        "id": "idx1",
        "fields": {"END": "LAST"},
        "inputs": {
            "VALUE": {"block": _text("abcabc")},
            "FIND": {"block": _text("bc")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "5"  # 1-based


async def test_text_index_of_not_found() -> None:
    block = {
        "type": "text_indexOf",
        "id": "idx1",
        "fields": {"END": "FIRST"},
        "inputs": {
            "VALUE": {"block": _text("abc")},
            "FIND": {"block": _text("xyz")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "0"


# ---------------------------------------------------------------------------
# text_charAt
# ---------------------------------------------------------------------------


async def test_text_char_at_from_start() -> None:
    num = {"type": "math_number", "id": "n1", "fields": {"NUM": "2"}}
    block = {
        "type": "text_charAt",
        "id": "c1",
        "fields": {"WHERE": "FROM_START"},
        "inputs": {
            "VALUE": {"block": _text("Hello")},
            "AT": {"block": num},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "e"  # index 2 (1-based) = 'e'


async def test_text_char_at_first() -> None:
    block = {
        "type": "text_charAt",
        "id": "c1",
        "fields": {"WHERE": "FIRST"},
        "inputs": {"VALUE": {"block": _text("Hello")}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "H"


async def test_text_char_at_last() -> None:
    block = {
        "type": "text_charAt",
        "id": "c1",
        "fields": {"WHERE": "LAST"},
        "inputs": {"VALUE": {"block": _text("Hello")}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "o"


# ---------------------------------------------------------------------------
# text_getSubstring
# ---------------------------------------------------------------------------


async def test_text_get_substring() -> None:
    num1 = {"type": "math_number", "id": "n1", "fields": {"NUM": "2"}}
    num2 = {"type": "math_number", "id": "n2", "fields": {"NUM": "4"}}
    block = {
        "type": "text_getSubstring",
        "id": "sub1",
        "fields": {"WHERE1": "FROM_START", "WHERE2": "FROM_START"},
        "inputs": {
            "STRING": {"block": _text("Hello World")},
            "AT1": {"block": num1},
            "AT2": {"block": num2},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "ell"  # index 2-4 (1-based) = chars at 1,2,3


async def test_text_get_substring_first_last() -> None:
    block = {
        "type": "text_getSubstring",
        "id": "sub1",
        "fields": {"WHERE1": "FIRST", "WHERE2": "LAST"},
        "inputs": {"STRING": {"block": _text("Hello")}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "Hello"


# ---------------------------------------------------------------------------
# text_changeCase
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "input_text", "expected"),
    [
        ("UPPERCASE", "hello", "HELLO"),
        ("LOWERCASE", "HELLO", "hello"),
        ("TITLECASE", "hello world", "Hello World"),
    ],
)
async def test_text_change_case(case: str, input_text: str, expected: str) -> None:
    block = {
        "type": "text_changeCase",
        "id": "cc1",
        "fields": {"CASE": case},
        "inputs": {"TEXT": {"block": _text(input_text)}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == expected


# ---------------------------------------------------------------------------
# text_trim
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "input_text", "expected"),
    [
        ("BOTH", "  hello  ", "hello"),
        ("LEFT", "  hello  ", "hello  "),
        ("RIGHT", "  hello  ", "  hello"),
    ],
)
async def test_text_trim(mode: str, input_text: str, expected: str) -> None:
    block = {
        "type": "text_trim",
        "id": "tr1",
        "fields": {"MODE": mode},
        "inputs": {"TEXT": {"block": _text(input_text)}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == expected
