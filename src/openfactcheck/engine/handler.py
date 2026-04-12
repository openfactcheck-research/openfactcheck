"""Block handler registration via decorator.

Register a handler by decorating a function with ``@handler``::

    @handler("text_print")
    def text_print(block: Block, ctx: ExecutionContext) -> None:
        ctx.print(resolve.string(block, ctx, "TEXT"))

Handlers are registered at import time — importing the module is
sufficient to make the handler available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from openfactcheck.engine.block import Block
    from openfactcheck.engine.context import ExecutionContext

    type HandlerFn = Callable[[Block, ExecutionContext], Any]

HANDLERS: dict[str, HandlerFn] = {}
"""Global registry mapping block type strings to handler functions."""


def handler(block_type: str) -> Callable[[HandlerFn], HandlerFn]:
    """Decorator that registers a function as a block handler.

    Args:
        block_type: The Blockly block type string (e.g. ``"text_print"``).

    Returns:
        The unmodified function, now registered in :data:`HANDLERS`.
    """

    def decorator(fn: HandlerFn) -> HandlerFn:
        HANDLERS[block_type] = fn
        return fn

    return decorator
