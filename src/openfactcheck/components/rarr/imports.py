"""Lazy import of the optional reranking dependency.

The cross-encoder used to select the attribution report ships in the ``rarr``
extra, not the base install, so it is imported on first use and a missing one
raises a clear install hint rather than an ``ImportError`` at module load.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.components.rarr.errors import RARRConfigError

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

_INSTALL_HINT = "install the extra with: pip install openfactcheck[rarr]"


def load_cross_encoder() -> type[CrossEncoder]:
    """Lazily import and return the ``CrossEncoder`` reranker class.

    Raises:
        RARRConfigError: ``sentence-transformers`` is not installed.
    """
    try:
        from sentence_transformers import CrossEncoder  # noqa: PLC0415 - lazy import for optional dependency.
    except ImportError:
        raise RARRConfigError(f"RARR evidence selection needs sentence-transformers; {_INSTALL_HINT}") from None
    return CrossEncoder
