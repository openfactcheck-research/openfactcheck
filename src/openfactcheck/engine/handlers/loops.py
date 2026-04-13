"""Loop block handlers — ``controls_repeat_ext``, ``controls_for``, etc."""

from openfactcheck.engine import resolve
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler

MAX_ITERATIONS = 10_000
"""Safety limit to prevent infinite loops."""


class BreakLoop(Exception):
    """Raised by controls_flow_statements to break out of a loop."""


class ContinueLoop(Exception):
    """Raised by controls_flow_statements to skip to the next iteration."""


@handler("controls_repeat_ext")
def controls_repeat_ext(block: Block, ctx: ExecutionContext) -> None:
    """Repeat the DO body TIMES times."""
    times = min(resolve.integer(block, ctx, "TIMES"), MAX_ITERATIONS)
    for _ in range(times):
        try:
            resolve.run_statements(block, ctx, "DO")
        except BreakLoop:
            break
        except ContinueLoop:
            continue


@handler("controls_whileUntil")
def controls_while_until(block: Block, ctx: ExecutionContext) -> None:
    """While or until loop. MODE field: WHILE or UNTIL."""
    mode = block.get_field("MODE", default="WHILE")
    for _ in range(MAX_ITERATIONS):
        condition = resolve.boolean(block, ctx, "BOOL")
        if (mode == "WHILE" and not condition) or (mode == "UNTIL" and condition):
            break
        try:
            resolve.run_statements(block, ctx, "DO")
        except BreakLoop:
            break
        except ContinueLoop:
            pass


@handler("controls_for")
def controls_for(block: Block, ctx: ExecutionContext) -> None:
    """For loop with a counter variable (VAR) from FROM to TO by BY."""
    var = block.get_field("VAR", default="i")
    from_val = resolve.num(block, ctx, "FROM")
    to_val = resolve.num(block, ctx, "TO")
    by_val = resolve.num(block, ctx, "BY")

    if by_val == 0 or (by_val > 0 and from_val > to_val) or (by_val < 0 and from_val < to_val):
        return

    value = from_val
    for _ in range(MAX_ITERATIONS):
        if (by_val > 0 and value > to_val) or (by_val < 0 and value < to_val):
            break
        ctx.variables[var] = value
        try:
            resolve.run_statements(block, ctx, "DO")
        except BreakLoop:
            break
        except ContinueLoop:
            pass
        value += by_val


@handler("controls_forEach")
def controls_for_each(block: Block, ctx: ExecutionContext) -> None:
    """For-each over a list. VAR field: variable name for the current item."""
    var = block.get_field("VAR", default="item")
    items = resolve.items(block, ctx, "LIST")
    for item in items[:MAX_ITERATIONS]:
        ctx.variables[var] = item
        try:
            resolve.run_statements(block, ctx, "DO")
        except BreakLoop:
            break
        except ContinueLoop:
            continue


@handler("controls_flow_statements")
def controls_flow_statements(block: Block, ctx: ExecutionContext) -> None:
    """Break or continue. FLOW field: BREAK or CONTINUE."""
    if block.get_field("FLOW", default="BREAK") == "BREAK":
        raise BreakLoop
    raise ContinueLoop
