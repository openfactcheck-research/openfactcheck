"""Tests for list block handlers."""

from typing import Any

import pytest

from openfactcheck.engine import execute_pipeline

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"blocks": {"blocks": list(blocks)}}


def _text(value: str, *, block_id: str = "t1") -> dict[str, Any]:
    return {"type": "text", "id": block_id, "fields": {"TEXT": value}}


def _num(value: float, *, block_id: str = "n1") -> dict[str, Any]:
    return {"type": "math_number", "id": block_id, "fields": {"NUM": str(value)}}


def _print(value_block: dict[str, Any]) -> dict[str, Any]:
    return {"type": "text_print", "id": "p1", "inputs": {"TEXT": {"block": value_block}}}


def _list(*items: dict[str, Any]) -> dict[str, Any]:
    inputs = {f"ADD{i}": {"block": item} for i, item in enumerate(items)}
    return {"type": "lists_create_with", "id": "list1", "inputs": inputs}


# ---------------------------------------------------------------------------
# lists_create_with
# ---------------------------------------------------------------------------


async def test_lists_create_with() -> None:
    block = _list(_num(1), _num(2), _num(3))
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "[1.0, 2.0, 3.0]"


async def test_lists_create_with_empty() -> None:
    block = {"type": "lists_create_with", "id": "list1", "inputs": {}}
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "[]"


async def test_lists_create_with_strings() -> None:
    block = _list(_text("a"), _text("b", block_id="t2"))
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "['a', 'b']"


# ---------------------------------------------------------------------------
# lists_repeat
# ---------------------------------------------------------------------------


async def test_lists_repeat() -> None:
    block = {
        "type": "lists_repeat",
        "id": "rep1",
        "inputs": {
            "ITEM": {"block": _text("x")},
            "NUM": {"block": _num(3)},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "['x', 'x', 'x']"


# ---------------------------------------------------------------------------
# lists_length
# ---------------------------------------------------------------------------


async def test_lists_length() -> None:
    block = {
        "type": "lists_length",
        "id": "len1",
        "inputs": {"VALUE": {"block": _list(_num(1), _num(2), _num(3))}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "3"


async def test_lists_length_empty() -> None:
    block = {
        "type": "lists_length",
        "id": "len1",
        "inputs": {"VALUE": {"block": {"type": "lists_create_with", "id": "l1", "inputs": {}}}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "0"


# ---------------------------------------------------------------------------
# lists_isEmpty
# ---------------------------------------------------------------------------


async def test_lists_is_empty_true() -> None:
    block = {
        "type": "lists_isEmpty",
        "id": "ie1",
        "inputs": {"VALUE": {"block": {"type": "lists_create_with", "id": "l1", "inputs": {}}}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "True"


async def test_lists_is_empty_false() -> None:
    block = {
        "type": "lists_isEmpty",
        "id": "ie1",
        "inputs": {"VALUE": {"block": _list(_num(1))}},
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "False"


# ---------------------------------------------------------------------------
# lists_indexOf
# ---------------------------------------------------------------------------


async def test_lists_index_of_first() -> None:
    block = {
        "type": "lists_indexOf",
        "id": "idx1",
        "fields": {"END": "FIRST"},
        "inputs": {
            "VALUE": {"block": _list(_text("a"), _text("b", block_id="t2"), _text("a", block_id="t3"))},
            "FIND": {"block": _text("a", block_id="t4")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "1"  # 1-based


async def test_lists_index_of_last() -> None:
    block = {
        "type": "lists_indexOf",
        "id": "idx1",
        "fields": {"END": "LAST"},
        "inputs": {
            "VALUE": {"block": _list(_text("a"), _text("b", block_id="t2"), _text("a", block_id="t3"))},
            "FIND": {"block": _text("a", block_id="t4")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "3"  # 1-based


async def test_lists_index_of_not_found() -> None:
    block = {
        "type": "lists_indexOf",
        "id": "idx1",
        "fields": {"END": "FIRST"},
        "inputs": {
            "VALUE": {"block": _list(_text("a"), _text("b", block_id="t2"))},
            "FIND": {"block": _text("z", block_id="t3")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "0"


# ---------------------------------------------------------------------------
# lists_getIndex
# ---------------------------------------------------------------------------


async def test_lists_get_index_from_start() -> None:
    block = {
        "type": "lists_getIndex",
        "id": "gi1",
        "fields": {"MODE": "GET", "WHERE": "FROM_START"},
        "inputs": {
            "VALUE": {"block": _list(_text("a"), _text("b", block_id="t2"), _text("c", block_id="t3"))},
            "AT": {"block": _num(2)},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "b"  # 1-based index 2


async def test_lists_get_index_first() -> None:
    block = {
        "type": "lists_getIndex",
        "id": "gi1",
        "fields": {"MODE": "GET", "WHERE": "FIRST"},
        "inputs": {
            "VALUE": {"block": _list(_text("x"), _text("y", block_id="t2"))},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "x"


async def test_lists_get_index_last() -> None:
    block = {
        "type": "lists_getIndex",
        "id": "gi1",
        "fields": {"MODE": "GET", "WHERE": "LAST"},
        "inputs": {
            "VALUE": {"block": _list(_text("x"), _text("y", block_id="t2"))},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "y"


# ---------------------------------------------------------------------------
# lists_getSublist
# ---------------------------------------------------------------------------


async def test_lists_get_sublist() -> None:
    block = {
        "type": "lists_getSublist",
        "id": "sub1",
        "fields": {"WHERE1": "FROM_START", "WHERE2": "FROM_START"},
        "inputs": {
            "LIST": {"block": _list(_num(10), _num(20, block_id="n2"), _num(30, block_id="n3"), _num(40, block_id="n4"))},
            "AT1": {"block": _num(2, block_id="at1")},
            "AT2": {"block": _num(3, block_id="at2")},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "[20.0, 30.0]"


async def test_lists_get_sublist_first_last() -> None:
    block = {
        "type": "lists_getSublist",
        "id": "sub1",
        "fields": {"WHERE1": "FIRST", "WHERE2": "LAST"},
        "inputs": {
            "LIST": {"block": _list(_num(1), _num(2, block_id="n2"), _num(3, block_id="n3"))},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "[1.0, 2.0, 3.0]"


# ---------------------------------------------------------------------------
# lists_sort
# ---------------------------------------------------------------------------


async def test_lists_sort_numeric() -> None:
    block = {
        "type": "lists_sort",
        "id": "sort1",
        "fields": {"TYPE": "NUMERIC", "DIRECTION": "1"},
        "inputs": {
            "LIST": {"block": _list(_num(3), _num(1, block_id="n2"), _num(2, block_id="n3"))},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "[1.0, 2.0, 3.0]"


async def test_lists_sort_text_descending() -> None:
    block = {
        "type": "lists_sort",
        "id": "sort1",
        "fields": {"TYPE": "TEXT", "DIRECTION": "-1"},
        "inputs": {
            "LIST": {"block": _list(_text("a"), _text("c", block_id="t2"), _text("b", block_id="t3"))},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "['c', 'b', 'a']"


# ---------------------------------------------------------------------------
# lists_reverse
# ---------------------------------------------------------------------------


async def test_lists_reverse() -> None:
    block = {
        "type": "lists_reverse",
        "id": "rev1",
        "inputs": {
            "LIST": {"block": _list(_num(1), _num(2, block_id="n2"), _num(3, block_id="n3"))},
        },
    }
    result = await execute_pipeline(_pipeline(_print(block)))
    assert result.output == "[3.0, 2.0, 1.0]"
