"""Graph executor — walks Blockly workspace JSON and runs block handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from openfactcheck.engine.context import BlockDict, EngineError, ExecutionContext, execute_block, get_dict


@dataclass
class ExecutionResult:
    """Result of a pipeline execution."""

    success: bool
    output: str
    error: str | None = None


def _execute_block_chain(block: BlockDict, ctx: ExecutionContext) -> None:
    """Execute a block and all its 'next' connected blocks."""
    execute_block(block, ctx)
    next_data = get_dict(block, "next")
    if next_data is None:
        return
    next_block = get_dict(next_data, "block")
    if next_block is not None:
        _execute_block_chain(next_block, ctx)


async def execute_pipeline(pipeline: BlockDict) -> ExecutionResult:
    """Execute a Blockly workspace JSON.

    Walks all top-level block chains, executing each block via its registered handler.
    """
    ctx = ExecutionContext()
    try:
        blocks_data = get_dict(pipeline, "blocks")
        if blocks_data is None:
            return ExecutionResult(success=True, output="")

        top_level_blocks: object = blocks_data.get("blocks")
        if not isinstance(top_level_blocks, list):
            return ExecutionResult(success=True, output="")

        for item in cast(list[Any], top_level_blocks):
            if isinstance(item, dict):
                _execute_block_chain(cast(BlockDict, item), ctx)

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
