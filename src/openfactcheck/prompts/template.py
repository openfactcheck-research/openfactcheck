"""Prompt templates: chat messages whose content carries ``{{variables}}``.

A template is an immutable record: a name, a declared variable contract, and
an ordered sequence of chat messages whose content carries ``{{placeholder}}``
references. Fill it against values to get a [`Prompt`][Prompt]
([`to_prompt`][PromptTemplate.to_prompt]), a chat message list
([`to_messages`][PromptTemplate.to_messages]), or a single string
([`to_string`][PromptTemplate.to_string]).

Build one from messages or ``(role, text)`` tuples in code, or load one from a
file (the extension selects the codec).

Example:
    ```python
    from openfactcheck.prompts import PromptTemplate

    verifier = PromptTemplate.from_messages(
        [
            ("system", "You are a fact-checker."),
            ("user", "Claim: {{claim}}"),
        ],
        name="verifier",
    )
    messages = verifier.to_messages(claim="The sky is green.")
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from openfactcheck.chat.messages import AssistantMessage, SystemMessage, UserMessage
from openfactcheck.prompts._substitution import find_placeholders, substitute
from openfactcheck.prompts.errors import (
    PromptNotFoundError,
    PromptValidationError,
    PromptVariableError,
)
from openfactcheck.prompts.prompt import Prompt
from openfactcheck.prompts.variables import VariableSpec

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from openfactcheck.chat.messages import Message
    from openfactcheck.prompts.variables import Role


_ROLE_TO_MESSAGE = {
    "system": SystemMessage,
    "user": UserMessage,
    "assistant": AssistantMessage,
}
"""Maps a tuple-shorthand role to the chat message type it builds."""


def _to_message(item: Message | tuple[Role, str]) -> Message:
    """Normalize a ``(role, text)`` tuple to a chat message, or pass one through."""
    if isinstance(item, tuple):
        role, content = item
        return _ROLE_TO_MESSAGE[role](content=content)
    return item


@dataclass(frozen=True, slots=True, eq=False)
class PromptTemplate:
    """An immutable, fillable prompt.

    Holds a stable ``name``, a declared variable contract, the chat messages
    that make up the template (content carries ``{{variables}}``), and an
    untyped ``metadata`` bucket for provenance. Equality compares
    ``(name, description, variables, messages)``; ``metadata`` is ignored, so
    two templates that differ only in provenance compare equal.
    """

    name: str
    """Stable identifier used to refer to this template, and used in equality.

    A programmatic identifier, not a display label; must be a non-empty valid
    Python identifier. [`description`][PromptTemplate.description] is the
    human-readable field.
    """

    description: str | None = None
    """Optional human-readable description."""

    variables: Mapping[str, VariableSpec] = field(default_factory=dict[str, VariableSpec])
    """Declared variable contract keyed by variable name.

    The contract is authoritative: a placeholder referencing no entry here is
    rejected at construction. A declared variable that appears in no message
    is allowed.
    """

    messages: tuple[Message, ...] = ()
    """The template's chat messages in authoring order, content carrying
    ``{{variables}}``.

    Repeated roles are permitted (for example user/assistant pairs for
    few-shot examples)."""

    metadata: Mapping[str, object] = field(default_factory=dict[str, object])
    """Non-semantic bucket for provenance and miscellany.

    Excluded from equality; callers should not branch logic on it."""

    def __post_init__(self) -> None:
        """Validate the name and variable contract, and freeze the mappings."""
        self._validate_name()
        self._validate_variable_names()
        self._validate_placeholder_references()
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def _validate_name(self) -> None:
        if not self.name or not self.name.isidentifier():
            raise PromptValidationError(
                path=None,
                line=None,
                reason="PromptTemplate.name must be a non-empty valid Python identifier",
                expected="[A-Za-z_][A-Za-z0-9_]*",
                got=repr(self.name),
            )

    def _validate_variable_names(self) -> None:
        for key, spec in self.variables.items():
            if key != spec.name:
                raise PromptValidationError(
                    path=None,
                    line=None,
                    reason=f"variables key {key!r} does not match VariableSpec.name {spec.name!r}",
                    expected=f"{key!r}",
                    got=f"{spec.name!r}",
                )
            if not key.isidentifier():
                raise PromptValidationError(
                    path=None,
                    line=None,
                    reason="variable name must be a valid identifier",
                    expected="[A-Za-z_][A-Za-z0-9_]*",
                    got=repr(key),
                )

    def _validate_placeholder_references(self) -> None:
        declared = set(self.variables)
        for index, message in enumerate(self.messages):
            referenced = find_placeholders(message.content)
            if undeclared := sorted(referenced - declared):
                raise PromptValidationError(
                    path=None,
                    line=index,
                    reason=f"message {index} references undeclared variable {undeclared[0]!r}",
                    expected=f"variable declared in PromptTemplate.variables: {undeclared[0]!r}",
                    got=f"placeholder {{{{{undeclared[0]}}}}} with no matching declaration",
                )

    def __eq__(self, other: object) -> bool:
        """Compare structure; ``metadata`` is intentionally excluded."""
        if not isinstance(other, PromptTemplate):
            return NotImplemented
        return (
            self.name == other.name
            and self.description == other.description
            and dict(self.variables) == dict(other.variables)
            and self.messages == other.messages
        )

    __hash__ = None  # pyright: ignore[reportAssignmentType] - PromptTemplate is intentionally unhashable.

    # -----------------------------------------------------------------
    # Filling
    # -----------------------------------------------------------------

    def to_prompt(self, **values: object) -> Prompt:
        """Substitute ``values`` into every message and return a [`Prompt`][Prompt].

        Args:
            **values: Values for the declared variables. Every required
                variable must be supplied; an omitted optional variable falls
                back to its [`default`][VariableSpec.default]. Unexpected
                names are rejected.

        Returns:
            A [`Prompt`][Prompt] wrapping the filled messages.

        Raises:
            PromptVariableError: A required variable is missing, or an
                unexpected variable was supplied.
        """
        required = {name for name, spec in self.variables.items() if spec.required}
        declared = set(self.variables)
        supplied = set(values)

        missing = tuple(sorted(required - supplied))
        unexpected = tuple(sorted(supplied - declared))
        if missing or unexpected:
            raise PromptVariableError(self.name, missing=missing, unexpected=unexpected)

        effective: dict[str, object] = dict(values)
        for name, spec in self.variables.items():
            if name not in effective and not spec.required:
                effective[name] = spec.default

        filled = tuple(
            message.model_copy(update={"content": substitute(message.content, effective)}) for message in self.messages
        )
        return Prompt(name=self.name, messages=filled, variables_used=effective)

    def to_messages(self, **values: object) -> list[Message]:
        """Fill the template and return the chat messages.

        Shortcut for ``self.to_prompt(**values).to_messages()``.
        """
        return self.to_prompt(**values).to_messages()

    def to_string(self, **values: object) -> str:
        """Fill the template and return one role-labeled string.

        Shortcut for ``self.to_prompt(**values).to_string()``.
        """
        return self.to_prompt(**values).to_string()

    # -----------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------

    @classmethod
    def from_messages(
        cls,
        messages: Sequence[Message | tuple[Role, str]],
        *,
        name: str,
        description: str | None = None,
        variables: Mapping[str, VariableSpec] | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> PromptTemplate:
        """Build a template from chat messages or ``(role, text)`` tuples.

        ``messages`` accepts chat message objects (whose content may carry
        ``{{variables}}``) or ``(role, text)`` tuples as a shorthand.

        If ``variables`` is omitted, the contract is inferred by scanning each
        message for ``{{placeholder}}`` references; each unique name becomes a
        required string variable. When ``variables`` is supplied, the contract
        is authoritative: a referenced-but-undeclared placeholder raises
        [`PromptValidationError`][PromptValidationError]; a declared-but-unused
        variable is allowed.

        Args:
            messages: Template messages in authoring order.
            name: Stable identifier.
            description: Optional human-readable description.
            variables: Optional explicit variable contract; inferred when omitted.
            metadata: Optional provenance bucket (for example, set by a codec).

        Returns:
            A validated template.

        Raises:
            PromptValidationError: Any domain invariant is violated.
        """
        normalized = tuple(_to_message(item) for item in messages)
        if variables is None:
            inferred: dict[str, VariableSpec] = {}
            for message in normalized:
                for placeholder in find_placeholders(message.content):
                    inferred.setdefault(placeholder, VariableSpec.string(placeholder))
            variables = inferred
        return cls(
            name=name,
            description=description,
            variables=variables,
            messages=normalized,
            metadata=metadata if metadata is not None else {},
        )

    @classmethod
    def from_template(cls, template: str, *, role: Role = "user", name: str) -> PromptTemplate:
        """Build a single-message template.

        Args:
            template: Message content, which may carry ``{{variables}}``.
            role: Role for the single message. Defaults to ``"user"``.
            name: Stable identifier.
        """
        return cls.from_messages([(role, template)], name=name)

    @classmethod
    def from_markdown(cls, text: str, *, name_hint: str | None = None) -> PromptTemplate:
        """Decode ``text`` as a markdown prompt.

        Args:
            text: Markdown source with YAML frontmatter and role-tagged body
                blocks.
            name_hint: Name to fall back to or verify against the frontmatter.

        Returns:
            The decoded template.

        Raises:
            PromptFormatError: The text is malformed for the markdown codec.
            PromptValidationError: The decoded template violates a domain
                invariant.
        """
        from openfactcheck.prompts.codecs.markdown import MarkdownPromptCodec  # noqa: PLC0415 - avoid circular import.

        return MarkdownPromptCodec().decode(text, name_hint=name_hint)

    @classmethod
    def from_file(cls, path: str | Path) -> PromptTemplate:
        """Load a template from a file, routing on the file extension.

        The extension selects the codec (``.md`` and ``.markdown`` route to the
        markdown codec); the filename stem is passed as the name hint.

        Args:
            path: Path to a prompt file.

        Returns:
            The decoded template.

        Raises:
            PromptNotFoundError: No file exists at ``path``.
            PromptFormatError: No codec is registered for the extension, or the
                source is malformed for the matched codec.
            PromptValidationError: The decoded template violates a domain
                invariant.
        """
        from openfactcheck.prompts.codecs import codec_for_path  # noqa: PLC0415 - avoid circular import.

        file_path = Path(path)
        if not file_path.is_file():
            raise PromptNotFoundError(file_path.stem, (file_path,))
        text = file_path.read_text(encoding="utf-8")
        return codec_for_path(file_path).decode(text, name_hint=file_path.stem)
