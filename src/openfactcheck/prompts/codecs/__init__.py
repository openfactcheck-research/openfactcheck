"""Serialization formats for prompts.

The [`PromptCodec`][PromptCodec] Protocol is the extension seam.
[`MarkdownPromptCodec`][MarkdownPromptCodec] is the one concrete codec
that ships in v1; future codecs (YAML, JSON) register their file
extensions in [`codec_for_path`][openfactcheck.prompts.codecs.codec_for_path]
and become loadable through [`PromptTemplate.from_file`][PromptTemplate.from_file]
with no further change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.prompts.codecs.markdown import MarkdownPromptCodec
from openfactcheck.prompts.codecs.protocol import PromptCodec
from openfactcheck.prompts.errors import PromptFormatError

if TYPE_CHECKING:
    from pathlib import Path

_MARKDOWN = MarkdownPromptCodec()

_CODEC_BY_SUFFIX: dict[str, PromptCodec] = {
    ".md": _MARKDOWN,
    ".markdown": _MARKDOWN,
}
"""File extension (lowercased, with leading dot) to the codec that handles it."""


def codec_for_path(path: Path) -> PromptCodec:
    """Return the codec registered for ``path``'s file extension.

    Args:
        path: File path whose suffix selects the codec.

    Returns:
        The codec registered for the suffix.

    Raises:
        PromptFormatError: No codec is registered for the suffix.
    """
    codec = _CODEC_BY_SUFFIX.get(path.suffix.lower())
    if codec is None:
        supported = ", ".join(sorted(_CODEC_BY_SUFFIX))
        raise PromptFormatError(
            path=path,
            line=None,
            reason="no codec registered for this file extension",
            expected=f"one of: {supported}",
            got=path.suffix or "(none)",
        )
    return codec


__all__ = ["MarkdownPromptCodec", "PromptCodec", "codec_for_path"]
