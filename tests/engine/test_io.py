"""Tests for the Input & Output block handlers."""

import json
from typing import cast

import pytest
from pydantic import BaseModel

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_text_input_value_returns_text() -> None:
    ctx = ExecutionContext()
    block = Block({"type": "text_input_value", "fields": {"INPUT_TEXT": "a claim"}})

    assert ctx.execute_block(block) == "a claim"


async def test_text_input_stores_variable() -> None:
    ctx = ExecutionContext()
    block = Block({"type": "text_input", "fields": {"INPUT_TEXT": "a claim"}})

    ctx.execute_block(block)

    assert ctx.variables["input_text"] == "a claim"


async def test_structured_output_builds_model() -> None:
    ctx = ExecutionContext()
    schema = [
        {"name": "verdict", "type": "bool", "asList": False, "description": "Whether it is true"},
        {"name": "scores", "type": "int", "asList": True},
    ]
    block = Block({"type": "structured_output", "fields": {"SCHEMA_DATA": json.dumps(schema)}})

    model = cast("type[BaseModel]", ctx.execute_block(block))

    assert issubclass(model, BaseModel)
    instance = model(verdict=True, scores=[1, 2, 3])
    assert instance.verdict is True
    assert instance.scores == [1, 2, 3]


async def test_structured_output_nested_dict() -> None:
    ctx = ExecutionContext()
    schema = [{"name": "meta", "type": "dict", "asList": False, "children": [{"name": "id", "type": "str", "asList": False}]}]
    block = Block({"type": "structured_output", "fields": {"SCHEMA_DATA": json.dumps(schema)}})

    model = cast("type[BaseModel]", ctx.execute_block(block))
    instance = model(meta={"id": "abc"})

    assert instance.meta.id == "abc"


async def test_structured_output_empty_schema() -> None:
    ctx = ExecutionContext()
    block = Block({"type": "structured_output", "fields": {"SCHEMA_DATA": "[]"}})

    model = cast("type[BaseModel]", ctx.execute_block(block))

    assert issubclass(model, BaseModel)
