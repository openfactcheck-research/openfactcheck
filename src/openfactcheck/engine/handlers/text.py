"""Text block handlers.

Handles Blockly's built-in text blocks:

- ``text_print`` — Statement block that prints a value to the output.
- ``text`` — Value block that returns a string literal.
"""

from __future__ import annotations

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import BlockHandler


class TextPrintHandler(BlockHandler):
    """``text_print`` — prints the value connected to the TEXT input.

    Blockly structure::

        text_print
        └─ TEXT (value input) → connected block's return value is printed
    """

    block_type = "text_print"

    def execute(self, block: Block, ctx: ExecutionContext) -> None:
        input_block = block.get_input_block("TEXT")
        value = ctx.execute_block(input_block) if input_block else ""
        ctx.print(str(value))


class TextHandler(BlockHandler):
    """``text`` — returns the string stored in the TEXT field.

    This is Blockly's basic string literal block. It has no inputs —
    just a single field containing the user's text.
    """

    block_type = "text"

    def execute(self, block: Block, ctx: ExecutionContext) -> str:
        return block.get_field("TEXT", default="")
