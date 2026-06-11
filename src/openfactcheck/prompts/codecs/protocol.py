"""The codec Protocol, the extension seam for prompt serialization formats.

Implementations translate between a [`PromptTemplate`][PromptTemplate] and a
text representation. Markdown is the one shipped codec; other formats (YAML,
JSON) are added by implementing this Protocol, with no other change to the
layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from openfactcheck.prompts.template import PromptTemplate


@runtime_checkable
class PromptCodec(Protocol):
    """Translate between a serialized representation and a [`PromptTemplate`][PromptTemplate].

    ``encode`` is best-effort: its output round-trips through
    [`decode`][PromptCodec.decode], but the exact byte layout (spacing, key
    ordering) is not part of the contract. Keep the authored source as the
    source of truth rather than relying on encode/decode to reproduce bytes.
    """

    def decode(self, text: str, *, name_hint: str | None = None) -> PromptTemplate:
        """Decode ``text`` into a [`PromptTemplate`][PromptTemplate].

        Args:
            text: Serialized representation.
            name_hint: Name to fall back to, or to verify against the
                source's own name field. File loading passes the filename
                stem so the codec can check it agrees with the declared name.

        Returns:
            The decoded template.

        Raises:
            PromptFormatError: The source could not be parsed by this codec.
            PromptValidationError: The decoded template violates a domain
                invariant.
        """
        ...

    def encode(self, template: PromptTemplate) -> str:
        """Encode ``template`` into this codec's text format.

        Args:
            template: Template to serialize.

        Returns:
            Serialized text.
        """
        ...
