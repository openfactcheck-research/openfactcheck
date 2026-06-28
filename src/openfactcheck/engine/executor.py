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

from dataclasses import dataclass
from typing import Any

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
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

    Any failure during execution (an :class:`EngineError`, a model/library
    error, or an unexpected exception) is caught and returned as a failed
    result, so a bad graph never crashes the runner.
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
    except Exception as e:  # noqa: BLE001 - any block or library failure becomes a failed run, not a crash.
        return ExecutionResult(
            success=False,
            output="\n".join(ctx.output_lines),
            error=str(e),
        )
