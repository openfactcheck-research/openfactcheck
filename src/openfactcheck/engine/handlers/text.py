"""Text block handlers — text_print and text."""

from __future__ import annotations

from typing import Any

from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import BlockHandler


class TextPrintHandler(BlockHandler):
    """Print block — outputs the connected text value."""

    block_type = "text_print"

    def execute(self, block: dict[str, Any], ctx: ExecutionContext) -> None:
        value = ctx.resolve_input(block, "TEXT", default="")
        ctx.print(str(value))


class TextHandler(BlockHandler):
    """Text literal block — returns the field value."""

    block_type = "text"

    def execute(self, block: dict[str, Any], ctx: ExecutionContext) -> str:
        return ctx.resolve_field(block, "TEXT", default="")
