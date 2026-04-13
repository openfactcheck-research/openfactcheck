"""Logic block handlers — ``logic_boolean``, ``controls_if``, etc."""

from typing import Any

from openfactcheck.engine import resolve
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler


@handler("logic_boolean")
def logic_boolean(block: Block, ctx: ExecutionContext) -> bool:
    """Return True or False from the BOOL field."""
    return block.get_field("BOOL", default="TRUE") == "TRUE"


@handler("logic_null")
def logic_null(block: Block, ctx: ExecutionContext) -> None:
    """Return None."""
    return None


@handler("logic_negate")
def logic_negate(block: Block, ctx: ExecutionContext) -> bool:
    """Logical NOT on the BOOL input."""
    return not resolve.boolean(block, ctx, "BOOL")


@handler("logic_compare")
def logic_compare(block: Block, ctx: ExecutionContext) -> bool:
    """Comparison of A and B inputs (EQ, NEQ, LT, LTE, GT, GTE)."""
    op = block.get_field("OP", default="EQ")
    a = resolve.value(block, ctx, "A")
    b = resolve.value(block, ctx, "B")
    if op == "EQ":
        return a == b
    if op == "NEQ":
        return a != b
    if op == "LT":
        return a < b  # type: ignore[operator]
    if op == "LTE":
        return a <= b  # type: ignore[operator]
    if op == "GT":
        return a > b  # type: ignore[operator]
    if op == "GTE":
        return a >= b  # type: ignore[operator]
    return False


@handler("logic_operation")
def logic_operation(block: Block, ctx: ExecutionContext) -> bool:
    """Logical AND/OR on A and B inputs."""
    op = block.get_field("OP", default="AND")
    a = resolve.value(block, ctx, "A")
    b = resolve.value(block, ctx, "B")
    return bool(a and b) if op == "AND" else bool(a or b)


@handler("logic_ternary")
def logic_ternary(block: Block, ctx: ExecutionContext) -> Any:  # noqa: ANN401
    """If IF is truthy, return THEN, else return ELSE."""
    if resolve.boolean(block, ctx, "IF"):
        return resolve.value(block, ctx, "THEN")
    return resolve.value(block, ctx, "ELSE")


@handler("controls_if")
def controls_if(block: Block, ctx: ExecutionContext) -> None:
    """If/elseif/else statement block with IF0/DO0, IF1/DO1, ..., ELSE."""
    i = 0
    while True:
        cond_block = block.get_input_block(f"IF{i}")
        if cond_block is None:
            break
        if ctx.execute_block(cond_block):
            resolve.run_statements(block, ctx, f"DO{i}")
            return
        i += 1
    resolve.run_statements(block, ctx, "ELSE")
