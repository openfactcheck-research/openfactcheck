"""Typed wrapper around a raw Blockly block dict.

This is the JSON boundary layer for the engine. Raw ``dict[str, Any]`` from
Blockly workspace serialization is parsed once on construction. After that,
all access is through typed attributes and methods — no raw dict access leaks
into the rest of the engine.

Blockly block JSON structure::

    {
        "type": "text_print",
        "id": "abc123",
        "fields": {"TEXT": "hello"},
        "inputs": {
            "TEXT": {
                "block": {"type": "text", "id": "xyz", "fields": {"TEXT": "world"}}
            }
        },
        "next": {
            "block": {"type": "text_print", "id": "def456", ...}
        }
    }
"""

from __future__ import annotations

from typing import Any


class Block:
    """A single Blockly block with typed access to fields, inputs, and connections.

    Attributes:
        type: Block type identifier (e.g. ``'text_print'``, ``'text'``).
        id: Unique block instance ID assigned by Blockly.

    """

    __slots__ = ("_extra", "_fields", "_inputs", "_next_data", "id", "type")

    def __init__(self, data: dict[str, Any]) -> None:
        self.type: str = str(data.get("type", ""))
        self.id: str = str(data.get("id", ""))
        self._fields: dict[str, str] = _parse_fields(data)
        self._inputs: dict[str, dict[str, Any]] = _parse_inputs(data)
        self._next_data: dict[str, Any] | None = _parse_next(data)
        self._extra: dict[str, Any] = _parse_extra(data)

    def get_field(self, name: str, default: str = "") -> str:
        """Read a static field value from the block.

        Fields are simple key-value pairs set directly on the block
        (e.g. the text content in a ``text`` block).
        """
        return self._fields.get(name, default)

    def get_extra(self, name: str, default: object = None) -> object:
        """Read a value from the block's ``extraState``.

        Some fields serialize their value into ``extraState`` rather than
        ``fields`` (for example a dropdown whose options load asynchronously),
        so a block's full configuration can span both.
        """
        return self._extra.get(name, default)

    def get_input_block(self, name: str) -> Block | None:
        """Get the block connected to a named value input.

        Value inputs are connection points where another block plugs in
        to provide a computed value (e.g. the ``TEXT`` input on ``text_print``).

        Returns ``None`` if no block is connected to this input.
        """
        input_data = self._inputs.get(name)
        if input_data is None:
            return None
        block_data = input_data.get("block")
        if not isinstance(block_data, dict):
            return None
        return Block(block_data)

    @property
    def next(self) -> Block | None:
        """The next block in the statement chain.

        Statement blocks connect vertically — each block's ``next`` points
        to the block below it. Returns ``None`` at the end of a chain.
        """
        if self._next_data is None:
            return None
        block_data = self._next_data.get("block")
        if not isinstance(block_data, dict):
            return None
        return Block(block_data)

    def __repr__(self) -> str:
        return f"Block(type={self.type!r}, id={self.id!r})"


def _parse_fields(data: dict[str, Any]) -> dict[str, str]:
    """Extract ``fields`` as a ``{name: value}`` string dict."""
    raw = data.get("fields")
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v is not None}


def _parse_inputs(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract ``inputs`` as a ``{name: input_data}`` dict, filtering non-dicts."""
    raw = data.get("inputs")
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _parse_next(data: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the ``next`` connection data, or ``None`` if absent."""
    raw = data.get("next")
    if isinstance(raw, dict):
        return raw
    return None


def _parse_extra(data: dict[str, Any]) -> dict[str, Any]:
    """Extract ``extraState`` as a dict, or empty if absent."""
    raw = data.get("extraState")
    return raw if isinstance(raw, dict) else {}
