"""Tests for logic block handlers."""

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


def _bool(value: bool) -> dict[str, Any]:
    return {"type": "logic_boolean", "id": "b1", "fields": {"BOOL": "TRUE" if value else "FALSE"}}


def _print(value_block: dict[str, Any]) -> dict[str, Any]:
    return {"type": "text_print", "id": "p1", "inputs": {"TEXT": {"block": value_block}}}


def _print_text(text: str, *, block_id: str = "p1") -> dict[str, Any]:
    return {
        "type": "text_print",
        "id": block_id,
        "inputs": {"TEXT": {"block": {"type": "text", "id": f"{block_id}_t", "fields": {"TEXT": text}}}},
    }


# ---------------------------------------------------------------------------
# logic_boolean
# ---------------------------------------------------------------------------


async def test_logic_boolean_true() -> None:
    result = await execute_pipeline(_pipeline(_print(_bool(True))))
    assert result.output == "True"


async def test_logic_boolean_false() -> None:
    result = await execute_pipeline(_pipeline(_print(_bool(False))))
    assert result.output == "False"


# ---------------------------------------------------------------------------
# logic_null
# ---------------------------------------------------------------------------


async def test_logic_null() -> None:
    block = {"type": "logic_null", "id": "null1"}
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "None"


# ---------------------------------------------------------------------------
# logic_negate
# ---------------------------------------------------------------------------


async def test_logic_negate_true() -> None:
    block = {"type": "logic_negate", "id": "neg1", "inputs": {"BOOL": {"block": _bool(True)}}}
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "False"


async def test_logic_negate_false() -> None:
    block = {"type": "logic_negate", "id": "neg1", "inputs": {"BOOL": {"block": _bool(False)}}}
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "True"


# ---------------------------------------------------------------------------
# logic_compare
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("op", "a", "b", "expected"),
    [
        ("EQ", 5, 5, "True"),
        ("EQ", 5, 3, "False"),
        ("NEQ", 5, 3, "True"),
        ("LT", 3, 5, "True"),
        ("LT", 5, 3, "False"),
        ("LTE", 5, 5, "True"),
        ("GT", 5, 3, "True"),
        ("GTE", 3, 5, "False"),
    ],
)
async def test_logic_compare(op: str, a: float, b: float, expected: str) -> None:
    block = {
        "type": "logic_compare",
        "id": "cmp1",
        "fields": {"OP": op},
        "inputs": {
            "A": {"block": _num(a)},
            "B": {"block": _num(b)},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == expected


# ---------------------------------------------------------------------------
# logic_operation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("op", "a", "b", "expected"),
    [
        ("AND", True, True, "True"),
        ("AND", True, False, "False"),
        ("OR", False, True, "True"),
        ("OR", False, False, "False"),
    ],
)
async def test_logic_operation(op: str, a: bool, b: bool, expected: str) -> None:
    block = {
        "type": "logic_operation",
        "id": "op1",
        "fields": {"OP": op},
        "inputs": {
            "A": {"block": _bool(a)},
            "B": {"block": _bool(b)},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == expected


# ---------------------------------------------------------------------------
# logic_ternary
# ---------------------------------------------------------------------------


async def test_logic_ternary_true() -> None:
    block = {
        "type": "logic_ternary",
        "id": "tern1",
        "inputs": {
            "IF": {"block": _bool(True)},
            "THEN": {"block": _text("yes")},
            "ELSE": {"block": _text("no")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "yes"


async def test_logic_ternary_false() -> None:
    block = {
        "type": "logic_ternary",
        "id": "tern1",
        "inputs": {
            "IF": {"block": _bool(False)},
            "THEN": {"block": _text("yes")},
            "ELSE": {"block": _text("no")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "no"


# ---------------------------------------------------------------------------
# controls_if
# ---------------------------------------------------------------------------


async def test_controls_if_true() -> None:
    block = {
        "type": "controls_if",
        "id": "if1",
        "inputs": {
            "IF0": {"block": _bool(True)},
            "DO0": {"block": _print_text("matched")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "matched"


async def test_controls_if_false() -> None:
    block = {
        "type": "controls_if",
        "id": "if1",
        "inputs": {
            "IF0": {"block": _bool(False)},
            "DO0": {"block": _print_text("nope")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == ""


async def test_controls_if_else() -> None:
    block = {
        "type": "controls_if",
        "id": "if1",
        "inputs": {
            "IF0": {"block": _bool(False)},
            "DO0": {"block": _print_text("if-branch")},
            "ELSE": {"block": _print_text("else-branch", block_id="p2")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "else-branch"


async def test_controls_if_elseif() -> None:
    block = {
        "type": "controls_if",
        "id": "if1",
        "inputs": {
            "IF0": {"block": _bool(False)},
            "DO0": {"block": _print_text("first")},
            "IF1": {"block": _bool(True)},
            "DO1": {"block": _print_text("second", block_id="p2")},
            "ELSE": {"block": _print_text("else", block_id="p3")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "second"


async def test_controls_if_with_chained_statements() -> None:
    """IF block with multiple statements chained via next."""
    stmt1 = _print_text("line1")
    stmt1["next"] = {"block": _print_text("line2", block_id="p2")}
    block = {
        "type": "controls_if",
        "id": "if1",
        "inputs": {
            "IF0": {"block": _bool(True)},
            "DO0": {"block": stmt1},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "line1\nline2"
