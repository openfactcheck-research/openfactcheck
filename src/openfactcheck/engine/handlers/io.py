"""Handlers for the Input & Output blocks: text input and structured output."""

import json
from typing import Any

from pydantic import BaseModel, Field, create_model

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler

# Schema field type to Python type; ``dict`` becomes a nested model when it has children.
_PY_TYPE: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}


@handler("text_input")
def text_input(block: Block, ctx: ExecutionContext) -> None:
    """Store the block's text as the ``input_text`` variable."""
    ctx.variables["input_text"] = block.get_field("INPUT_TEXT")


@handler("text_input_value")
def text_input_value(block: Block, _ctx: ExecutionContext) -> str:
    """Return the block's text as a value for a slot."""
    return block.get_field("INPUT_TEXT")


@handler("structured_output")
def structured_output(block: Block, _ctx: ExecutionContext) -> type[BaseModel]:
    """Build a Pydantic model from the block's schema."""
    try:
        fields = json.loads(block.get_field("SCHEMA_DATA", default="[]"))
    except json.JSONDecodeError:
        fields = []
    return _build_model("Output", fields if isinstance(fields, list) else [])


def _pascal(name: str) -> str:
    """Convert a field name to a PascalCase class name."""
    return "".join(part.capitalize() for part in name.split("_") if part) or "Field"


def _build_model(name: str, fields: list[Any]) -> type[BaseModel]:
    """Build a Pydantic model from a schema field list, recursing into ``dict`` fields."""
    definitions: dict[str, Any] = {}
    for field in fields:
        if not isinstance(field, dict):
            continue
        field_name = str(field.get("name") or "field")
        field_type = str(field.get("type", "str"))
        if field_type == "dict" and isinstance(field.get("children"), list):
            base: Any = _build_model(f"{name}{_pascal(field_name)}", field["children"])
        else:
            base = _PY_TYPE.get(field_type, str)
        annotation: Any = list[base] if field.get("asList") else base
        description = str(field.get("description") or "")
        definitions[field_name] = (annotation, Field(description=description) if description.strip() else ...)
    return create_model(name, **definitions)
