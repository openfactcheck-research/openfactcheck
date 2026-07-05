"""Tests for the Prompts block handler."""

from typing import cast

import pytest

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.prompts import PromptTemplate

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_prompt_template_builds_system_and_user() -> None:
    ctx = ExecutionContext()
    block = Block({"type": "prompt_template", "fields": {"SYSTEM_TEXT": "You are a checker.", "USER_TEXT": "Claim: {{claim}}"}})

    template = cast("PromptTemplate", ctx.execute_block(block))

    assert isinstance(template, PromptTemplate)
    assert "claim" in template.variables
    messages = template.to_messages(claim="The sky is green.")
    assert [m.role for m in messages] == ["system", "user"]
    assert messages[1].content == "Claim: The sky is green."


async def test_prompt_template_user_only() -> None:
    ctx = ExecutionContext()
    block = Block({"type": "prompt_template", "fields": {"SYSTEM_TEXT": "", "USER_TEXT": "Just user."}})

    template = cast("PromptTemplate", ctx.execute_block(block))

    assert [m.role for m in template.to_messages()] == ["user"]


async def test_prompt_template_system_only_becomes_user() -> None:
    ctx = ExecutionContext()
    block = Block({"type": "prompt_template", "fields": {"SYSTEM_TEXT": "Check {{claim}}", "USER_TEXT": ""}})

    template = cast("PromptTemplate", ctx.execute_block(block))

    messages = template.to_messages(claim="X")
    assert [m.role for m in messages] == ["user"]
    assert messages[0].content == "Check X"
    assert "claim" in template.variables


async def test_prompt_template_builds_from_message_turns() -> None:
    ctx = ExecutionContext()
    block = Block({
        "type": "prompt_template",
        "extraState": {
            "messages": [
                {"role": "system", "content": "You are a checker."},
                {"role": "user", "content": "Claim: {{claim}}"},
                {"role": "assistant", "content": "Verifying."},
                {"role": "user", "content": "Now: {{claim}}"},
            ],
        },
    })

    template = cast("PromptTemplate", ctx.execute_block(block))

    assert [m.role for m in template.to_messages(claim="X")] == ["system", "user", "assistant", "user"]
    assert "claim" in template.variables


async def test_prompt_template_skips_empty_turns() -> None:
    ctx = ExecutionContext()
    block = Block({
        "type": "prompt_template",
        "extraState": {
            "messages": [
                {"role": "system", "content": "   "},
                {"role": "user", "content": "Only this."},
            ],
        },
    })

    template = cast("PromptTemplate", ctx.execute_block(block))

    messages = template.to_messages()
    assert [m.role for m in messages] == ["user"]
    assert messages[0].content == "Only this."


async def test_prompt_template_prefers_messages_over_legacy_fields() -> None:
    ctx = ExecutionContext()
    block = Block({
        "type": "prompt_template",
        "fields": {"SYSTEM_TEXT": "legacy", "USER_TEXT": "legacy user"},
        "extraState": {"messages": [{"role": "user", "content": "new turn"}]},
    })

    template = cast("PromptTemplate", ctx.execute_block(block))

    messages = template.to_messages()
    assert [m.role for m in messages] == ["user"]
    assert messages[0].content == "new turn"
