"""Markdown serialization for the markdown codec."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import yaml

from openfactcheck.prompts.codecs.markdown._constants import ROLE_H1

if TYPE_CHECKING:
    from openfactcheck.messages import Message
    from openfactcheck.prompts.template import PromptTemplate
    from openfactcheck.prompts.variables import Role


def emit_markdown(template: PromptTemplate) -> str:
    """Serialize a template to the markdown format."""
    frontmatter: dict[str, Any] = {"name": template.name}
    version = template.metadata.get("version")
    if isinstance(version, int):
        frontmatter["version"] = version
    if template.description is not None:
        frontmatter["description"] = template.description
    if template.variables:
        frontmatter["variables"] = {
            name: {"type": spec.type, "required": spec.required} for name, spec in template.variables.items()
        }

    frontmatter_text = yaml.safe_dump(frontmatter, sort_keys=False).strip()
    blocks = [_emit_block(message) for message in template.messages]
    return f"---\n{frontmatter_text}\n---\n\n" + "\n\n".join(blocks) + "\n"


def _emit_block(message: Message) -> str:
    """Render one message as its ``<role>`` block with the canonical H1."""
    role = cast("Role", message.role)
    h1 = ROLE_H1[role]
    return f"<{role}>\n\n{h1}\n\n{message.content}\n\n</{role}>"
