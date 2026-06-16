"""The filled prompt value produced by [`PromptTemplate.to_prompt`][PromptTemplate.to_prompt].

A [`Prompt`][Prompt] holds the chat messages a template produced after its
variables were substituted, plus the values that were used. Convert it to a
chat message list with [`to_messages`][Prompt.to_messages] or to a single
role-labeled string with [`to_string`][Prompt.to_string].

Example:
    ```python
    prompt = template.to_prompt(claim="X", evidence="Y")
    response = client.completion(prompt.to_messages())
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from openfactcheck.messages import Message


@dataclass(frozen=True, slots=True)
class Prompt:
    """A template filled with values, ready to send to a model.

    Wraps the chat messages produced by
    [`PromptTemplate.to_prompt`][PromptTemplate.to_prompt], in authoring
    order, alongside the values that were substituted.
    """

    name: str
    """Identifier of the source [`PromptTemplate`][PromptTemplate]."""

    messages: tuple[Message, ...]
    """The filled chat messages, in authoring order."""

    variables_used: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))
    """Values substituted when the template was filled (supplied kwargs plus
    any optional defaults).

    An immutable view over a private copy; mutating the caller's original
    kwargs does not affect it.
    """

    def __post_init__(self) -> None:
        """Freeze ``variables_used`` as an immutable view over a copy."""
        object.__setattr__(self, "variables_used", MappingProxyType(dict(self.variables_used)))

    def to_messages(self) -> list[Message]:
        """Return the filled messages as a list, ready for the chat client."""
        return list(self.messages)

    def to_string(self) -> str:
        """Return the messages as one role-labeled string.

        Each message renders as ``"<role>: <content>"``, joined by blank
        lines.
        """
        return "\n\n".join(f"{message.role}: {message.content}" for message in self.messages)
