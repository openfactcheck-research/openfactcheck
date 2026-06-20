"""Lazy imports of the optional scraping and reranking dependencies.

These packages ship in the ``factcheckgpt`` extra, not the base install, so they
are imported on first use and a missing one raises a clear install hint rather
than an ``ImportError`` at module load.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.integrations.google_scraper.errors import GoogleScraperConfigError

if TYPE_CHECKING:
    from bs4 import BeautifulSoup
    from sentence_transformers import CrossEncoder

_INSTALL_HINT = "install the extra with: pip install openfactcheck[factcheckgpt]"


def load_beautifulsoup() -> type[BeautifulSoup]:
    """Lazily import and return the ``BeautifulSoup`` HTML parser class.

    Raises:
        GoogleScraperConfigError: ``beautifulsoup4`` is not installed.
    """
    try:
        from bs4 import BeautifulSoup  # noqa: PLC0415 - lazy import for optional dependency.
    except ImportError:
        raise GoogleScraperConfigError(f"the Google scraper needs beautifulsoup4; {_INSTALL_HINT}") from None
    return BeautifulSoup


def load_cross_encoder() -> type[CrossEncoder]:
    """Lazily import and return the ``CrossEncoder`` reranker class.

    Raises:
        GoogleScraperConfigError: ``sentence-transformers`` is not installed.
    """
    try:
        from sentence_transformers import CrossEncoder  # noqa: PLC0415 - lazy import for optional dependency.
    except ImportError:
        raise GoogleScraperConfigError(f"the Google scraper needs sentence-transformers; {_INSTALL_HINT}") from None
    return CrossEncoder
