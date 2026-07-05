"""Handler for the Prompts block: prompt template."""

from typing import cast

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler
from openfactcheck.prompts import PromptTemplate, Role

_ROLES: frozenset[str] = frozenset({"system", "user", "assistant"})


@handler("prompt_template")
def prompt_template(block: Block, _ctx: ExecutionContext) -> PromptTemplate:
    """Build a prompt template from the block's ordered message turns.

    Turns live in ``extraState.messages`` as ``{"role", "content"}`` entries.
    Whitespace-only turns are dropped so an untouched row is not sent as an
    empty message. Blocks that predate multi-turn editing carry
    ``SYSTEM_TEXT``/``USER_TEXT`` fields instead, handled as a fallback.
    """
    messages = _turns_from_extra(block) or _turns_from_fields(block)
    return PromptTemplate.from_messages(messages, name="prompt_template")


def _turns_from_extra(block: Block) -> list[tuple[Role, str]]:
    """Read the ordered message turns from ``extraState``, dropping empty ones."""
    raw = block.get_extra("messages")
    if not isinstance(raw, list):
        return []
    turns: list[tuple[Role, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content", "")
        if role in _ROLES and isinstance(content, str) and content.strip():
            turns.append((cast("Role", role), content))
    return turns


def _turns_from_fields(block: Block) -> list[tuple[Role, str]]:
    """Fall back to the pre-multi-turn ``SYSTEM_TEXT``/``USER_TEXT`` fields."""
    system = block.get_field("SYSTEM_TEXT")
    user = block.get_field("USER_TEXT")
    turns: list[tuple[Role, str]] = []
    if system.strip() and user.strip():
        turns.append(("system", system))
    body = user if user.strip() else system
    if body.strip():
        turns.append(("user", body))
    return turns
