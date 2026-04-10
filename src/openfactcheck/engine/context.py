"""Execution context and engine errors.

:class:`ExecutionContext` is the mutable state object passed to every block
handler during a pipeline run. It provides:

- **Output capture** — :meth:`~ExecutionContext.print` collects output lines
  (with truncation at :data:`MAX_OUTPUT_BYTES`).
- **Variable storage** — ``variables`` dict for blocks that set/get variables.
- **Block dispatch** — :meth:`~ExecutionContext.execute_block` looks up a block's
  handler and runs it, enabling recursive execution of connected blocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openfactcheck.api.repositories.constants import MAX_OUTPUT_BYTES
from openfactcheck.engine.handler import BLOCK_HANDLERS

if TYPE_CHECKING:
    from openfactcheck.engine.block import Block


class EngineError(Exception):
    """Base exception for all engine execution failures.

    Caught by :func:`~openfactcheck.engine.executor.execute_pipeline` and
    converted to a failed :class:`~openfactcheck.engine.executor.ExecutionResult`.
    """


class UnknownBlockError(EngineError):
    """Raised when a block type has no registered handler.

    This typically means a block was added to the frontend toolbox
    but no corresponding :class:`~openfactcheck.engine.handler.BlockHandler`
    subclass exists on the server.
    """

    def __init__(self, block_type: str) -> None:
        super().__init__(f"No handler for block type: {block_type}")
        self.block_type = block_type


@dataclass
class ExecutionContext:
    """Mutable state passed to every block handler during execution.

    Created once per pipeline run by the executor. Handlers read/write
    through this context rather than managing their own state.

    Attributes:
        output_lines: Captured print output, one string per line.
        variables: Shared variable storage for ``variables_set``/``variables_get`` blocks.
    """

    output_lines: list[str] = field(default_factory=lambda: [])
    variables: dict[str, Any] = field(default_factory=lambda: {})
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

    def execute_block(self, block: Block) -> Any:  # noqa: ANN401
        """Dispatch a block to its registered handler and return the result.

        This is how handlers execute connected child blocks — e.g. a
        ``text_print`` handler calls ``ctx.execute_block(input_block)``
        to evaluate the text value plugged into its input.

        Raises:
            UnknownBlockError: If no handler is registered for ``block.type``.
        """
        handler = BLOCK_HANDLERS.get(block.type)
        if handler is None:
            raise UnknownBlockError(block.type)
        return handler.execute(block, self)
