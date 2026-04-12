"""Typed input resolution helpers for block handlers.

These functions are the single boundary between ``execute_block()`` (which
returns ``Any``) and handler code (which needs typed values). All type
coercion, ``try/except``, and ``type: ignore`` suppressions live here so
that handler files stay clean.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from openfactcheck.engine.block import Block
    from openfactcheck.engine.context import ExecutionContext


def num(block: Block, ctx: ExecutionContext, name: str, default: float = 0.0) -> float:
    """Resolve a value input to float."""
    input_block = block.get_input_block(name)
    if input_block is None:
        return default
    result = ctx.execute_block(input_block)
    try:
        return float(result)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def string(block: Block, ctx: ExecutionContext, name: str, default: str = "") -> str:
    """Resolve a value input to str."""
    input_block = block.get_input_block(name)
    if input_block is None:
        return default
    result = ctx.execute_block(input_block)
    return str(result) if result is not None else default


def boolean(block: Block, ctx: ExecutionContext, name: str, *, default: bool = False) -> bool:
    """Resolve a value input to bool."""
    input_block = block.get_input_block(name)
    if input_block is None:
        return default
    return bool(ctx.execute_block(input_block))


def integer(block: Block, ctx: ExecutionContext, name: str, default: int = 0) -> int:
    """Resolve a value input to int."""
    input_block = block.get_input_block(name)
    if input_block is None:
        return default
    result = ctx.execute_block(input_block)
    try:
        return int(float(result))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def value(block: Block, ctx: ExecutionContext, name: str) -> object:
    """Resolve any value input. Returns object (not Any) for type safety."""
    input_block = block.get_input_block(name)
    if input_block is None:
        return None
    result: object = ctx.execute_block(input_block)
    return result


def items(block: Block, ctx: ExecutionContext, name: str) -> list[object]:
    """Resolve a value input to a typed list."""
    input_block = block.get_input_block(name)
    if input_block is None:
        return []
    result = ctx.execute_block(input_block)
    if isinstance(result, list):
        return cast(list[object], result)
    return []


def run_statements(block: Block, ctx: ExecutionContext, name: str) -> None:
    """Execute a statement chain connected to the given input."""
    stmt = block.get_input_block(name)
    while stmt is not None:
        ctx.execute_block(stmt)
        stmt = stmt.next


def collect_inputs(block: Block, ctx: ExecutionContext, prefix: str = "ADD") -> list[object]:
    """Collect numbered value inputs (ADD0, ADD1, ...) into a list."""
    results: list[object] = []
    i = 0
    while True:
        input_block = block.get_input_block(f"{prefix}{i}")
        if input_block is None:
            break
        results.append(ctx.execute_block(input_block))
        i += 1
    return results
