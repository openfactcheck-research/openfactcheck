"""Variable block handlers — ``variables_get``, ``variables_set``."""

from typing import Any

from openfactcheck.engine import resolve
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler


@handler("variables_get")
def variables_get(block: Block, ctx: ExecutionContext) -> Any:  # noqa: ANN401
    """Return the value of the named variable."""
    return ctx.variables.get(block.get_field("VAR", default="item"), "")


@handler("variables_set")
def variables_set(block: Block, ctx: ExecutionContext) -> None:
    """Set the named variable to the VALUE input."""
    ctx.variables[block.get_field("VAR", default="item")] = resolve.value(block, ctx, "VALUE")
