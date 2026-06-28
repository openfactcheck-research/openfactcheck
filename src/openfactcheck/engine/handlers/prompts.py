"""Handler for the Prompts block: prompt template."""

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler
from openfactcheck.prompts import PromptTemplate, Role


@handler("prompt_template")
def prompt_template(block: Block, _ctx: ExecutionContext) -> PromptTemplate:
    """Build a prompt template from the block's system and user bodies.

    A completion needs a user turn, so a lone body (only one field filled)
    becomes the user message; a system message is added only when it accompanies
    a user prompt.
    """
    system = block.get_field("SYSTEM_TEXT")
    user = block.get_field("USER_TEXT")
    messages: list[tuple[Role, str]] = []
    if system.strip() and user.strip():
        messages.append(("system", system))
    messages.append(("user", user if user.strip() else system))
    return PromptTemplate.from_messages(messages, name="prompt_template")
