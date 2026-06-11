"""The markdown codec class: orchestrates frontmatter, body, and emit."""

from __future__ import annotations

from pathlib import Path

from openfactcheck.prompts.codecs.markdown._constants import ROLES
from openfactcheck.prompts.codecs.markdown.body import BodyParser
from openfactcheck.prompts.codecs.markdown.emit import emit_markdown
from openfactcheck.prompts.codecs.markdown.frontmatter import FrontMatterParser
from openfactcheck.prompts.errors import PromptFormatError
from openfactcheck.prompts.template import PromptTemplate


class MarkdownPromptCodec:
    """Default prompt codec: YAML frontmatter + role-tagged markdown body.

    Instances are stateless; construct one per call or share freely.
    """

    def decode(self, text: str, *, name_hint: str | None = None) -> PromptTemplate:
        """Decode markdown source into a [`PromptTemplate`][PromptTemplate].

        Args:
            text: Full file contents.
            name_hint: Filename stem (or equivalent) for error messages and
                for cross-checking against the frontmatter ``name``. If
                supplied and the frontmatter declares a name, the two must
                match.

        Returns:
            The decoded template.

        Raises:
            PromptFormatError: Source cannot be parsed by this codec.
            PromptValidationError: The decoded template violates a domain
                invariant.
        """
        path_for_errors = Path(name_hint) if name_hint else None
        frontmatter = FrontMatterParser(path=path_for_errors)
        frontmatter_lines, body_lines, body_start_line = frontmatter.split(text)
        name, version, description, variables = frontmatter.parse("\n".join(frontmatter_lines))

        if name_hint is not None and name != name_hint:
            raise PromptFormatError(
                path=path_for_errors,
                line=None,
                reason="frontmatter 'name' does not match name_hint",
                expected=name_hint,
                got=name,
            )

        blocks = BodyParser(path=path_for_errors).parse(body_lines, body_start_line=body_start_line)

        metadata: dict[str, object] = {"source": "markdown"}
        if version is not None:
            metadata["version"] = version

        return PromptTemplate.from_messages(
            blocks,
            name=name,
            description=description,
            variables=variables,
            metadata=metadata,
        )

    def encode(self, template: PromptTemplate) -> str:
        """Encode a [`PromptTemplate`][PromptTemplate] into this codec's markdown format.

        Round-trips through [`decode`][MarkdownPromptCodec.decode]; the exact
        byte layout is not part of the contract.

        Args:
            template: Template to serialize.

        Returns:
            Markdown text.

        Raises:
            PromptFormatError: The template repeats a role, or uses a role this
                codec does not emit.
        """
        seen_roles: set[str] = set()
        for message in template.messages:
            if message.role not in ROLES:
                raise PromptFormatError(
                    path=None,
                    line=None,
                    reason="markdown codec only emits system/user/assistant messages",
                    expected=f"one of {list(ROLES)}",
                    got=f"{message.role!r} message",
                )
            if message.role in seen_roles:
                raise PromptFormatError(
                    path=None,
                    line=None,
                    reason="markdown codec cannot encode repeated role blocks",
                    expected="at most one block of each role",
                    got=f"second {message.role!r} block",
                )
            seen_roles.add(message.role)
        return emit_markdown(template)
