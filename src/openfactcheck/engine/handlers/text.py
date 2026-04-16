"""Text block handlers — ``text``, ``text_print``, ``text_join``, etc."""

import random

from openfactcheck.engine import resolve
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler


@handler("text")
def text(block: Block, _ctx: ExecutionContext) -> str:
    """Return the string literal from the TEXT field."""
    return block.get_field("TEXT", default="")


@handler("text_print")
def text_print(block: Block, ctx: ExecutionContext) -> None:
    """Print the value connected to the TEXT input."""
    input_block = block.get_input_block("TEXT")
    val = ctx.execute_block(input_block) if input_block else ""
    ctx.print(str(val))


@handler("text_join")
def text_join(block: Block, ctx: ExecutionContext) -> str:
    """Concatenate numbered value inputs (ADD0, ADD1, ...)."""
    return "".join(str(v) for v in resolve.collect_inputs(block, ctx, "ADD"))


@handler("text_append")
def text_append(block: Block, ctx: ExecutionContext) -> None:
    """Append the TEXT input to a variable."""
    var = block.get_field("VAR", default="item")
    ctx.variables[var] = str(ctx.variables.get(var, "")) + resolve.string(block, ctx, "TEXT")


@handler("text_length")
def text_length(block: Block, ctx: ExecutionContext) -> int:
    """Return the length of the VALUE input string."""
    return len(resolve.string(block, ctx, "VALUE"))


@handler("text_isEmpty")
def text_is_empty(block: Block, ctx: ExecutionContext) -> bool:
    """Return True if the VALUE input is empty."""
    return len(resolve.string(block, ctx, "VALUE")) == 0


@handler("text_indexOf")
def text_index_of(block: Block, ctx: ExecutionContext) -> int:
    """Find the index of FIND in VALUE. Returns 0 if not found (1-based)."""
    end = block.get_field("END", default="FIRST")
    val = resolve.string(block, ctx, "VALUE")
    find = resolve.string(block, ctx, "FIND")
    idx = val.find(find) if end == "FIRST" else val.rfind(find)
    return idx + 1 if idx >= 0 else 0


@handler("text_charAt")
def text_char_at(block: Block, ctx: ExecutionContext) -> str:
    """Get a character from the VALUE input by position."""
    where = block.get_field("WHERE", default="FROM_START")
    val = resolve.string(block, ctx, "VALUE")
    if not val:
        return ""
    if where == "FIRST":
        return val[0]
    if where == "LAST":
        return val[-1]
    if where == "RANDOM":
        return random.choice(val)
    at = resolve.integer(block, ctx, "AT", default=1)
    idx = (at - 1) if where == "FROM_START" else (len(val) - at)
    return val[idx] if 0 <= idx < len(val) else ""


@handler("text_getSubstring")
def text_get_substring(block: Block, ctx: ExecutionContext) -> str:
    """Extract a substring from the STRING input."""
    val = resolve.string(block, ctx, "STRING")
    if not val:
        return ""
    start = _text_index(block, ctx, val, "WHERE1", "AT1")
    end = _text_index(block, ctx, val, "WHERE2", "AT2")
    return val[start : end + 1]


@handler("text_changeCase")
def text_change_case(block: Block, ctx: ExecutionContext) -> str:
    """Convert the TEXT input to upper/lower/title case."""
    case = block.get_field("CASE", default="UPPERCASE")
    val = resolve.string(block, ctx, "TEXT")
    if case == "UPPERCASE":
        return val.upper()
    if case == "LOWERCASE":
        return val.lower()
    if case == "TITLECASE":
        return val.title()
    return val


@handler("text_trim")
def text_trim(block: Block, ctx: ExecutionContext) -> str:
    """Trim whitespace from the TEXT input."""
    mode = block.get_field("MODE", default="BOTH")
    val = resolve.string(block, ctx, "TEXT")
    if mode == "BOTH":
        return val.strip()
    if mode == "LEFT":
        return val.lstrip()
    if mode == "RIGHT":
        return val.rstrip()
    return val


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text_index(block: Block, ctx: ExecutionContext, val: str, where_field: str, at_input: str) -> int:
    """Resolve a Blockly substring index (1-based) to a Python index (0-based)."""
    where = block.get_field(where_field, default="FROM_START")
    if where == "FIRST":
        return 0
    if where == "LAST":
        return len(val) - 1
    at = resolve.integer(block, ctx, at_input, default=1)
    return max(0, at - 1) if where == "FROM_START" else max(0, len(val) - at)
