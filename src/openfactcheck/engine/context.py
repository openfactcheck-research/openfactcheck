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
from openfactcheck.engine.events import OutputEvent, RunEvent
from openfactcheck.engine.handler import HANDLERS

MAX_OUTPUT_BYTES = 65_536

if TYPE_CHECKING:
    from collections.abc import Callable

    from openfactcheck.engine.block import Block


def _discard(_event: RunEvent) -> None:
    """Drop an event; the default when a run is not being streamed."""


@dataclass
class ExecutionContext:
    """Mutable state passed to every block handler during execution.

    Created once per pipeline run by the executor. Handlers read/write
    through this context rather than managing their own state.

    Attributes:
        output_lines: Captured print output, one string per line.
        variables: Shared variable storage for ``variables_set``/``variables_get`` blocks.
        streaming: Whether the run is being observed live; when set, handlers forward progress to ``emit``.
        emit: Sink for a run event; a no-op unless the run is streamed.

    """

    output_lines: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    streaming: bool = False
    emit: Callable[[RunEvent], None] = _discard
    _output_bytes: int = 0
    _truncated: bool = False

    def print(self, text: str) -> None:
        """Capture a line of output from a print block, and emit it when streaming.

        Respects :data:`MAX_OUTPUT_BYTES` — once the limit is reached, a
        ``[output truncated]`` marker is appended and all further prints are silently dropped.
        """
        if self._truncated:
            return
        line = str(text)
        line_bytes = len(line.encode())
        if self._output_bytes + line_bytes > MAX_OUTPUT_BYTES:
            self._append("[output truncated]")
            self._truncated = True
            return
        self._output_bytes += line_bytes
        self._append(line)

    def _append(self, line: str) -> None:
        """Record an output line, forwarding it as an event when streaming."""
        self.output_lines.append(line)
        if self.streaming:
            self.emit(OutputEvent(text=line))

    def execute_block(self, block: Block) -> object:
        """Dispatch a block to its registered handler and return the result.

        Raises:
            UnknownBlockError: If no handler is registered for ``block.type``.

        """
        handler_fn = HANDLERS.get(block.type)
        if handler_fn is None:
            raise UnknownBlockError(block.type)
        return handler_fn(block, self)
