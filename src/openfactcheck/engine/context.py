"""Execution context — carries state through a pipeline run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from openfactcheck.api.repositories.constants import MAX_OUTPUT_BYTES
from openfactcheck.engine.handler import BLOCK_HANDLERS


class EngineError(Exception):
    """Base error for engine execution failures."""


class UnknownBlockError(EngineError):
    """Raised when a block type has no registered handler."""

    def __init__(self, block_type: str) -> None:
        super().__init__(f"No handler for block type: {block_type}")
        self.block_type = block_type


BlockDict = dict[str, Any]


@dataclass
class ExecutionContext:
    """Mutable state passed to every block handler during execution."""

    output_lines: list[str] = field(default_factory=lambda: [])
    variables: dict[str, Any] = field(default_factory=lambda: {})
    _output_bytes: int = 0
    _truncated: bool = False

    def print(self, text: str) -> None:
        """Capture a print output line, respecting the output size limit."""
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

    def resolve_input(self, block: BlockDict, input_name: str, default: Any = None) -> Any:  # noqa: ANN401
        """Resolve a value input by executing the connected block."""
        inputs = get_dict(block, "inputs")
        if inputs is None:
            return default
        input_data = get_dict(inputs, input_name)
        if input_data is None:
            return default
        connected_block = get_dict(input_data, "block")
        if connected_block is None:
            return default
        return execute_block(connected_block, self)

    def resolve_field(self, block: BlockDict, field_name: str, default: Any = None) -> Any:  # noqa: ANN401
        """Read a field value directly from the block."""
        fields = get_dict(block, "fields")
        if fields is None:
            return default
        return fields.get(field_name, default)


def get_dict(source: BlockDict, key: str) -> BlockDict | None:
    """Safely extract a nested dict from a block dict. Returns None if missing or wrong type."""
    value: object = source.get(key)
    if isinstance(value, dict):
        return cast(BlockDict, value)
    return None


def execute_block(block: BlockDict, ctx: ExecutionContext) -> Any:  # noqa: ANN401
    """Execute a single block and return its value."""
    block_type: str = str(block.get("type", ""))
    handler = BLOCK_HANDLERS.get(block_type)
    if handler is None:
        raise UnknownBlockError(block_type)
    return handler.execute(block, ctx)
