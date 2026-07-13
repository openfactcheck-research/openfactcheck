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

import asyncio
import queue
import threading
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.events import FinishedEvent, RunEvent
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


def _run_blocks(pipeline: dict[str, Any], ctx: ExecutionContext) -> ExecutionResult:
    """Walk every top-level block chain and collect the outcome. The shared core of both run paths.

    Any failure during execution (an :class:`EngineError`, a model/library error, or an unexpected
    exception) is caught and returned as a failed result, so a bad graph never crashes the runner.
    """
    try:
        blocks = parse_pipeline(pipeline)
        if not blocks:
            return ExecutionResult(success=True, output="")

        for block in blocks:
            _execute_block_chain(block, ctx)

        return ExecutionResult(success=True, output="\n".join(ctx.output_lines))
    except Exception as e:  # noqa: BLE001 - any block or library failure becomes a failed run, not a crash.
        return ExecutionResult(success=False, output="\n".join(ctx.output_lines), error=str(e))


async def execute_pipeline(pipeline: dict[str, Any]) -> ExecutionResult:
    """Execute a Blockly workspace JSON end-to-end, returning the captured output or error.

    1. Parses the workspace JSON into a list of top-level :class:`Block` objects.
    2. Walks each block chain, executing handlers via the :class:`ExecutionContext`.
    3. Returns an :class:`ExecutionResult` with captured output or error.
    """
    return _run_blocks(pipeline, ExecutionContext())


async def stream_pipeline(pipeline: dict[str, Any]) -> AsyncGenerator[RunEvent]:
    """Execute a Blockly workspace JSON and yield run events as they happen.

    The blocks run in a worker thread so their synchronous handlers can push events onto a queue
    while this coroutine drains and yields them. The last event is always a :class:`FinishedEvent`
    carrying the run's success and final output.

    Yields:
        Each :class:`~openfactcheck.engine.events.RunEvent` in turn, ending with a finished event.
    """
    events: queue.Queue[RunEvent | None] = queue.Queue()
    ctx = ExecutionContext(streaming=True, emit=events.put)

    def worker() -> None:
        try:
            result = _run_blocks(pipeline, ctx)
            events.put(FinishedEvent(success=result.success, output=result.output, error=result.error))
        finally:
            events.put(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    loop = asyncio.get_running_loop()
    try:
        while (event := await loop.run_in_executor(None, events.get)) is not None:
            yield event
    finally:
        await loop.run_in_executor(None, thread.join)
