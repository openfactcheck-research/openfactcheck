"""Block handler registry — ABC base class with auto-registration via __init_subclass__."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from openfactcheck.engine.context import ExecutionContext

BLOCK_HANDLERS: dict[str, BlockHandler] = {}


class BlockHandler(ABC):
    """Base class for all block handlers.

    Subclasses must define ``block_type`` and implement ``execute``.
    Registration is automatic — subclassing is enough.
    """

    block_type: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "block_type") and isinstance(cls.__dict__.get("block_type"), str):
            BLOCK_HANDLERS[cls.block_type] = cls()

    @abstractmethod
    def execute(self, block: dict[str, Any], ctx: ExecutionContext) -> Any:  # noqa: ANN401
        """Execute the block and return its value (if any)."""
        ...
