"""Execution context — mutable state passed to every block handler.

:class:`ExecutionContext` provides:

- **Output capture** — :meth:`~ExecutionContext.print` collects output lines
  (with truncation at :data:`MAX_OUTPUT_BYTES`).
- **Variable storage** — ``variables`` dict for blocks that set/get variables.
- **Block dispatch** — :meth:`~ExecutionContext.execute_block` looks up a block's
  handler and runs it, enabling recursive execution of connected blocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openfactcheck.engine.errors import UnknownBlockError
from openfactcheck.engine.handler import HANDLERS

MAX_OUTPUT_BYTES = 65_536

if TYPE_CHECKING:
    from openfactcheck.engine.block import Block


@dataclass
class ExecutionContext:
    """Mutable state passed to every block handler during execution.

    Created once per pipeline run by the executor. Handlers read/write
    through this context rather than managing their own state.

    Attributes:
        output_lines: Captured print output, one string per line.
        variables: Shared variable storage for ``variables_set``/``variables_get`` blocks.

    """

    output_lines: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    _output_bytes: int = 0
    _truncated: bool = False

    def print(self, text: str) -> None:
        """Capture a line of output from a print block.

        Respects :data:`MAX_OUTPUT_BYTES` — once the limit is reached, a
        ``[output truncated]`` marker is appended and all further prints are silently dropped.
        """
        if self._truncated:
            return
        line = str(text)
        line_bytes = len(line.encode())
        if self._output_bytes + line_bytes > MAX_OUTPUT_BYTES:
            self.output_lines.append("[output truncated]")
            self._truncated = True
            return
        self._output_bytes += line_bytes
        self.output_lines.append(line)

    def execute_block(self, block: Block) -> object:
        """Dispatch a block to its registered handler and return the result.

        Raises:
            UnknownBlockError: If no handler is registered for ``block.type``.

        """
        handler_fn = HANDLERS.get(block.type)
        if handler_fn is None:
            raise UnknownBlockError(block.type)
        return handler_fn(block, self)
