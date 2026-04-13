"""Tests for math block handlers."""

import math
from typing import Any

import pytest

from openfactcheck.engine import execute_pipeline

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"blocks": {"blocks": list(blocks)}}


def _num(value: float) -> dict[str, Any]:
    return {"type": "math_number", "id": "n1", "fields": {"NUM": str(value)}}


def _print_value(value_block: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "text_print",
        "id": "p1",
        "inputs": {"TEXT": {"block": value_block}},
    }


def _arithmetic(op: str, a: float, b: float) -> dict[str, Any]:
    return {
        "type": "math_arithmetic",
        "id": "arith1",
        "fields": {"OP": op},
        "inputs": {
            "A": {"block": _num(a)},
            "B": {"block": _num(b)},
        },
    }


def _single(op: str, n: float) -> dict[str, Any]:
    return {
        "type": "math_single",
        "id": "single1",
        "fields": {"OP": op},
        "inputs": {"NUM": {"block": _num(n)}},
    }


def _trig(op: str, n: float) -> dict[str, Any]:
    return {
        "type": "math_trig",
        "id": "trig1",
        "fields": {"OP": op},
        "inputs": {"NUM": {"block": _num(n)}},
    }


# ---------------------------------------------------------------------------
# math_number
# ---------------------------------------------------------------------------


async def test_math_number() -> None:
    result = await execute_pipeline(_pipeline(_print_value(_num(42))))
    assert result.output == "42.0"


async def test_math_number_decimal() -> None:
    result = await execute_pipeline(_pipeline(_print_value(_num(3.14))))
    assert result.output == "3.14"


# ---------------------------------------------------------------------------
# math_arithmetic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("op", "a", "b", "expected"),
    [
        ("ADD", 3, 4, "7.0"),
        ("MINUS", 10, 3, "7.0"),
        ("MULTIPLY", 6, 7, "42.0"),
        ("DIVIDE", 10, 4, "2.5"),
        ("POWER", 2, 10, "1024.0"),
    ],
)
async def test_math_arithmetic(op: str, a: float, b: float, expected: str) -> None:
    result = await execute_pipeline(_pipeline(_print_value(_arithmetic(op, a, b))))
    assert result.output == expected


async def test_math_divide_by_zero() -> None:
    result = await execute_pipeline(_pipeline(_print_value(_arithmetic("DIVIDE", 5, 0))))
    assert result.output == "inf"


# ---------------------------------------------------------------------------
# math_single
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("op", "n", "expected"),
    [
        ("ROOT", 9, 3.0),
        ("ABS", -5, 5.0),
        ("NEG", 7, -7.0),
        ("LN", math.e, 1.0),
        ("LOG10", 100, 2.0),
        ("EXP", 0, 1.0),
        ("POW10", 3, 1000.0),
    ],
)
async def test_math_single(op: str, n: float, expected: float) -> None:
    result = await execute_pipeline(_pipeline(_print_value(_single(op, n))))
    assert float(result.output) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# math_trig
# ---------------------------------------------------------------------------


async def test_math_trig_sin() -> None:
    result = await execute_pipeline(_pipeline(_print_value(_trig("SIN", 90))))
    assert float(result.output) == pytest.approx(1.0)


async def test_math_trig_cos() -> None:
    result = await execute_pipeline(_pipeline(_print_value(_trig("COS", 0))))
    assert float(result.output) == pytest.approx(1.0)


async def test_math_trig_atan() -> None:
    result = await execute_pipeline(_pipeline(_print_value(_trig("ATAN", 1))))
    assert float(result.output) == pytest.approx(45.0)


# ---------------------------------------------------------------------------
# math_constant
# ---------------------------------------------------------------------------


async def test_math_constant_pi() -> None:
    block = {"type": "math_constant", "id": "c1", "fields": {"CONSTANT": "PI"}}
    result = await execute_pipeline(_pipeline(_print_value(block)))
    assert float(result.output) == pytest.approx(math.pi)


async def test_math_constant_infinity() -> None:
    block = {"type": "math_constant", "id": "c1", "fields": {"CONSTANT": "INFINITY"}}
    result = await execute_pipeline(_pipeline(_print_value(block)))
    assert result.output == "inf"


# ---------------------------------------------------------------------------
# math_number_property
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("prop", "n", "expected"),
    [
        ("EVEN", 4, "True"),
        ("EVEN", 5, "False"),
        ("ODD", 7, "True"),
        ("PRIME", 13, "True"),
        ("PRIME", 4, "False"),
        ("WHOLE", 5.0, "True"),
        ("WHOLE", 5.5, "False"),
        ("POSITIVE", 3, "True"),
        ("NEGATIVE", -1, "True"),
    ],
)
async def test_math_number_property(prop: str, n: float, expected: str) -> None:
    block = {
        "type": "math_number_property",
        "id": "prop1",
        "fields": {"PROPERTY": prop},
        "inputs": {"NUMBER_TO_CHECK": {"block": _num(n)}},
    }
    result = await execute_pipeline(_pipeline(_print_value(block)))
    assert result.output == expected


# ---------------------------------------------------------------------------
# math_round
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("op", "n", "expected"),
    [
        ("ROUND", 3.5, "4"),
        ("ROUNDUP", 3.1, "4"),
        ("ROUNDDOWN", 3.9, "3"),
    ],
)
async def test_math_round(op: str, n: float, expected: str) -> None:
    block = {
        "type": "math_round",
        "id": "r1",
        "fields": {"OP": op},
        "inputs": {"NUM": {"block": _num(n)}},
    }
    result = await execute_pipeline(_pipeline(_print_value(block)))
    assert result.output == expected


# ---------------------------------------------------------------------------
# math_modulo
# ---------------------------------------------------------------------------


async def test_math_modulo() -> None:
    block = {
        "type": "math_modulo",
        "id": "m1",
        "inputs": {
            "DIVIDEND": {"block": _num(10)},
            "DIVISOR": {"block": _num(3)},
        },
    }
    result = await execute_pipeline(_pipeline(_print_value(block)))
    assert result.output == "1.0"


# ---------------------------------------------------------------------------
# math_constrain
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "low", "high", "expected"),
    [
        (5, 1, 10, "5.0"),
        (-5, 1, 10, "1.0"),
        (15, 1, 10, "10.0"),
    ],
)
async def test_math_constrain(value: float, low: float, high: float, expected: str) -> None:
    block = {
        "type": "math_constrain",
        "id": "con1",
        "inputs": {
            "VALUE": {"block": _num(value)},
            "LOW": {"block": _num(low)},
            "HIGH": {"block": _num(high)},
        },
    }
    result = await execute_pipeline(_pipeline(_print_value(block)))
    assert result.output == expected


# ---------------------------------------------------------------------------
# math_random_int
# ---------------------------------------------------------------------------


async def test_math_random_int_in_range() -> None:
    block = {
        "type": "math_random_int",
        "id": "ri1",
        "inputs": {
            "FROM": {"block": _num(1)},
            "TO": {"block": _num(10)},
        },
    }
    result = await execute_pipeline(_pipeline(_print_value(block)))
    value = int(float(result.output))
    assert 1 <= value <= 10


# ---------------------------------------------------------------------------
# math_random_float
# ---------------------------------------------------------------------------


async def test_math_random_float_in_range() -> None:
    block = {"type": "math_random_float", "id": "rf1"}
    result = await execute_pipeline(_pipeline(_print_value(block)))
    value = float(result.output)
    assert 0.0 <= value < 1.0


# ---------------------------------------------------------------------------
# math_on_list
# ---------------------------------------------------------------------------


def _list(*values: float) -> dict[str, Any]:
    inputs = {f"ADD{i}": {"block": _num(v)} for i, v in enumerate(values)}
    return {"type": "lists_create_with", "id": "list1", "inputs": inputs}


def _math_on_list(op: str, *values: float) -> dict[str, Any]:
    return {
        "type": "math_on_list",
        "id": "mol1",
        "fields": {"OP": op},
        "inputs": {"LIST": {"block": _list(*values)}},
    }


@pytest.mark.parametrize(
    ("op", "values", "expected"),
    [
        ("SUM", (1, 2, 3), 6.0),
        ("MIN", (5, 2, 8), 2.0),
        ("MAX", (5, 2, 8), 8.0),
        ("AVERAGE", (2, 4, 6), 4.0),
        ("MEDIAN", (1, 3, 2), 2.0),
        ("MEDIAN", (1, 2, 3, 4), 2.5),
        ("MODE", (1, 2, 2, 3), 2.0),
    ],
)
async def test_math_on_list(op: str, values: tuple[float, ...], expected: float) -> None:
    result = await execute_pipeline(_pipeline(_print_value(_math_on_list(op, *values))))
    assert float(result.output) == pytest.approx(expected)


async def test_math_on_list_std_dev() -> None:
    result = await execute_pipeline(_pipeline(_print_value(_math_on_list("STD_DEV", 2, 4, 4, 4, 5, 5, 7, 9))))
    assert float(result.output) == pytest.approx(2.0)


async def test_math_on_list_random() -> None:
    result = await execute_pipeline(_pipeline(_print_value(_math_on_list("RANDOM", 10, 20, 30))))
    assert float(result.output) in (10.0, 20.0, 30.0)
