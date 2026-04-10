"""Block handler base class with auto-registration.

New handlers are created by subclassing :class:`BlockHandler` and setting
``block_type``. Registration into :data:`BLOCK_HANDLERS` is automatic via
``__init_subclass__`` — no decorator or manual registration needed::

    class TextPrintHandler(BlockHandler):
        block_type = "text_print"

        def execute(self, block: Block, ctx: ExecutionContext) -> None:
            ctx.print(block.get_field("TEXT"))
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from openfactcheck.engine.block import Block
    from openfactcheck.engine.context import ExecutionContext

BLOCK_HANDLERS: dict[str, BlockHandler] = {}
"""Global registry mapping block type strings to handler instances."""


class BlockHandler(ABC):
    """Base class for all block handlers.

    Subclasses must:
        1. Set ``block_type`` as a class variable (the Blockly block type string).
        2. Implement :meth:`execute` to define the block's behavior.

    A singleton instance is created and registered automatically when the
    subclass is defined (via ``__init_subclass__``). Handlers must be stateless
    — the same instance is reused across all runs.
    """

    block_type: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "block_type") and isinstance(cls.__dict__.get("block_type"), str):
            BLOCK_HANDLERS[cls.block_type] = cls()

    @abstractmethod
    def execute(self, block: Block, ctx: ExecutionContext) -> Any:  # noqa: ANN401
        """Execute the block and return its output value.

        Args:
            block: The parsed Blockly block with typed field/input access.
            ctx: Mutable execution context for output capture, variable storage,
                 and dispatching child block execution.

        Returns:
            The block's output value (used by parent blocks via value inputs),
            or ``None`` for statement-only blocks like ``text_print``.
        """
        ...
