"""Pipeline executor — the top-level entry point for running a Blockly workspace.

Flow::

    execute_pipeline(workspace_json)
        → parse_pipeline → list[Block]
        → for each top-level block:
            _execute_block_chain(block, ctx)
                → ctx.execute_block(block)  (dispatches to handler)
                → follow block.next recursively
        → collect output → ExecutionResult
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import EngineError, ExecutionContext
from openfactcheck.engine.parser import parse_pipeline


@dataclass
class ExecutionResult:
    """Outcome of a pipeline execution.

    Attributes:
        success: ``True`` if the pipeline completed without engine errors.
        output: Captured stdout (newline-joined print output).
        error: Error message if ``success`` is ``False``, otherwise ``None``.
    """

    success: bool
    output: str
    error: str | None = None


def _execute_block_chain(block: Block, ctx: ExecutionContext) -> None:
    """Execute a block and follow the ``next`` chain until the end.

    This handles Blockly's statement connection model — blocks stack
    vertically and execute top-to-bottom.
    """
    ctx.execute_block(block)
    next_block = block.next
    if next_block is not None:
        _execute_block_chain(next_block, ctx)


async def execute_pipeline(pipeline: dict[str, Any]) -> ExecutionResult:
    """Execute a Blockly workspace JSON end-to-end.

    1. Parses the workspace JSON into a list of top-level :class:`Block` objects.
    2. Walks each block chain, executing handlers via the :class:`ExecutionContext`.
    3. Returns an :class:`ExecutionResult` with captured output or error.

    Any :class:`EngineError` raised during execution is caught and returned
    as a failed result. Other exceptions propagate to the caller.
    """
    ctx = ExecutionContext()
    try:
        blocks = parse_pipeline(pipeline)
        if not blocks:
            return ExecutionResult(success=True, output="")

        for block in blocks:
            _execute_block_chain(block, ctx)

        return ExecutionResult(
            success=True,
            output="\n".join(ctx.output_lines),
        )
    except EngineError as e:
        return ExecutionResult(
            success=False,
            output="\n".join(ctx.output_lines),
            error=str(e),
        )
