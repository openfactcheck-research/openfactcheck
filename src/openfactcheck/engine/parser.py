# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Blockly workspace JSON parser — extracts top-level blocks from workspace state."""

from typing import Any

from openfactcheck.engine.block import Block


def parse_pipeline(pipeline: dict[str, Any]) -> list[Block]:
    """Extract the top-level block list from a Blockly workspace JSON.

    Handles both formats:
        - Real Blockly: ``{ blocks: { blocks: { language_version, blocks: [...] } } }``
        - Flat:         ``{ blocks: { blocks: [...] } }``

    Returns an empty list if the pipeline has no blocks.
    """
    blocks_wrapper = pipeline.get("blocks")
    if not isinstance(blocks_wrapper, dict):
        return []

    blocks_inner = blocks_wrapper.get("blocks")

    # Real Blockly format: blocks_inner is a dict with language_version + blocks list
    if isinstance(blocks_inner, dict):
        raw_blocks = blocks_inner.get("blocks")
    # Flat format: blocks_inner is already the list
    elif isinstance(blocks_inner, list):
        raw_blocks = blocks_inner
    else:
        return []

    if not isinstance(raw_blocks, list):
        return []

    return [Block(item) for item in raw_blocks if isinstance(item, dict)]
