"""List block handlers — ``lists_create_with``, ``lists_sort``, etc."""

from __future__ import annotations

from openfactcheck.engine import resolve
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler


@handler("lists_create_with")
def lists_create_with(block: Block, ctx: ExecutionContext) -> list[object]:
    """Create a list from ADD0, ADD1, ... inputs."""
    return resolve.collect_inputs(block, ctx, "ADD")


@handler("lists_repeat")
def lists_repeat(block: Block, ctx: ExecutionContext) -> list[object]:
    """Create a list by repeating ITEM, NUM times."""
    return [resolve.value(block, ctx, "ITEM")] * resolve.integer(block, ctx, "NUM")


@handler("lists_length")
def lists_length(block: Block, ctx: ExecutionContext) -> int:
    """Return the length of the VALUE input list."""
    return len(resolve.items(block, ctx, "VALUE"))


@handler("lists_isEmpty")
def lists_is_empty(block: Block, ctx: ExecutionContext) -> bool:
    """Return True if the VALUE input list is empty."""
    return len(resolve.items(block, ctx, "VALUE")) == 0


@handler("lists_indexOf")
def lists_index_of(block: Block, ctx: ExecutionContext) -> int:
    """Find the index of FIND in the list. Returns 0 if not found (1-based)."""
    end = block.get_field("END", default="FIRST")
    items = resolve.items(block, ctx, "VALUE")
    find = resolve.value(block, ctx, "FIND")

    if end == "FIRST":
        try:
            return items.index(find) + 1
        except ValueError:
            return 0
    for i in range(len(items) - 1, -1, -1):
        if items[i] == find:
            return i + 1
    return 0


@handler("lists_getIndex")
def lists_get_index(block: Block, ctx: ExecutionContext) -> object:
    """Get/remove an element. MODE: GET, GET_REMOVE, REMOVE. WHERE: FROM_START, FROM_END, FIRST, LAST, RANDOM."""
    mode = block.get_field("MODE", default="GET")
    items = resolve.items(block, ctx, "VALUE")
    if not items:
        return None
    idx = _list_index(block, ctx, items)
    if idx < 0 or idx >= len(items):
        return None
    if mode == "GET":
        return items[idx]
    if mode == "GET_REMOVE":
        return items.pop(idx)
    items.pop(idx)
    return None


@handler("lists_setIndex")
def lists_set_index(block: Block, ctx: ExecutionContext) -> None:
    """Set or insert an element. MODE: SET, INSERT."""
    mode = block.get_field("MODE", default="SET")
    items = resolve.items(block, ctx, "LIST")
    val = resolve.value(block, ctx, "TO")
    if not items:
        return
    idx = _list_index(block, ctx, items)
    if mode == "SET" and 0 <= idx < len(items):
        items[idx] = val
    elif mode == "INSERT":
        items.insert(max(0, idx), val)


@handler("lists_getSublist")
def lists_get_sublist(block: Block, ctx: ExecutionContext) -> list[object]:
    """Extract a sublist from LIST."""
    items = resolve.items(block, ctx, "LIST")
    if not items:
        return []
    start = _list_index_range(block, ctx, items, "WHERE1", "AT1")
    end = _list_index_range(block, ctx, items, "WHERE2", "AT2")
    return items[start : end + 1]


@handler("lists_sort")
def lists_sort(block: Block, ctx: ExecutionContext) -> list[object]:
    """Sort a list. TYPE: NUMERIC, TEXT, IGNORE_CASE. DIRECTION: 1 or -1."""
    sort_type = block.get_field("TYPE", default="NUMERIC")
    reverse = block.get_field("DIRECTION", default="1") == "-1"
    result = list(resolve.items(block, ctx, "LIST"))

    key_fn = _sort_numeric
    if sort_type == "TEXT":
        key_fn = _sort_text
    elif sort_type == "IGNORE_CASE":
        key_fn = _sort_ignore_case
    result.sort(key=key_fn, reverse=reverse)
    return result


@handler("lists_reverse")
def lists_reverse(block: Block, ctx: ExecutionContext) -> list[object]:
    """Reverse a list."""
    return list(reversed(resolve.items(block, ctx, "LIST")))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_index(block: Block, ctx: ExecutionContext, items: list[object]) -> int:
    """Resolve a list index from WHERE field + AT input."""
    where = block.get_field("WHERE", default="FROM_START")
    if where == "FIRST":
        return 0
    if where == "LAST":
        return len(items) - 1
    if where == "RANDOM":
        import random

        return random.randrange(len(items)) if items else 0
    at = resolve.integer(block, ctx, "AT", default=1)
    return (at - 1) if where == "FROM_START" else (len(items) - at)


def _list_index_range(block: Block, ctx: ExecutionContext, items: list[object], where_field: str, at_input: str) -> int:
    """Resolve a sublist index."""
    where = block.get_field(where_field, default="FROM_START")
    if where == "FIRST":
        return 0
    if where == "LAST":
        return len(items) - 1
    at = resolve.integer(block, ctx, at_input, default=1)
    return max(0, at - 1) if where == "FROM_START" else max(0, len(items) - at)


def _sort_numeric(x: object) -> float:
    try:
        return float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _sort_text(x: object) -> str:
    return str(x)


def _sort_ignore_case(x: object) -> str:
    return str(x).lower()
