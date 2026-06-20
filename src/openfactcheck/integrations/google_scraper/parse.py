"""HTML and text helpers for the Google scraper integration.

Pure functions that turn raw HTML into result URLs and visible text, and split
text into overlapping passages. The reranker scores these passages; the client
wires them together.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from openfactcheck.integrations.google_scraper.imports import load_beautifulsoup

# Hosts and paths that are Google's own chrome, not organic results.
_NON_RESULT_MARKERS = ("google.", "gstatic.", "googleusercontent.", "/search?", "/preferences", "/policies")

# Tags whose text is never page content.
_INVISIBLE_TAGS = ("script", "style", "head", "title", "meta", "noscript", "template")

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def extract_result_urls(html: str, *, limit: int) -> list[str]:
    """Return organic result URLs from a Google search results page, in order.

    Args:
        html: The raw HTML of a Google search results page.
        limit: Maximum number of URLs to return.

    Returns:
        Deduplicated external result URLs, capped at ``limit``.
    """
    soup = load_beautifulsoup()(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        url = _result_url(str(anchor["href"]))
        if url is None or url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def extract_visible_text(html: str) -> str:
    """Return the visible text of a page with whitespace collapsed.

    Args:
        html: The raw HTML of a web page.

    Returns:
        The page's visible text, or an empty string when nothing is extractable.
    """
    soup = load_beautifulsoup()(html, "html.parser")
    for tag in soup(list(_INVISIBLE_TAGS)):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def chunk_passages(
    text: str,
    *,
    sentences_per_passage: int,
    sliding_distance: int,
    max_sentence_chars: int = 250,
) -> list[str]:
    """Split text into overlapping passages with a sliding window over sentences.

    Args:
        text: The page text to split.
        sentences_per_passage: Number of sentences per passage (the window size).
        sliding_distance: Sentences to advance between passages; clamped to the
            window size so passages stay contiguous.
        max_sentence_chars: Sentences longer than this are dropped as likely
            boilerplate or metadata.

    Returns:
        The passages, in document order.
    """
    sentences = [
        sentence for raw in _SENTENCE_BOUNDARY.split(text) if 0 < len(sentence := raw.strip()) <= max_sentence_chars
    ]
    step = sliding_distance if 0 < sliding_distance <= sentences_per_passage else sentences_per_passage
    passages: list[str] = []
    for start in range(0, len(sentences), step):
        passage = " ".join(sentences[start : start + sentences_per_passage])
        if passage:
            passages.append(passage)
        if start + sentences_per_passage >= len(sentences):
            break
    return passages


def _result_url(href: str) -> str | None:
    """Resolve an anchor ``href`` to an organic result URL, or ``None`` to skip it."""
    if href.startswith("/url?"):
        target = parse_qs(urlparse(href).query).get("q")
        href = target[0] if target else ""
    if not href.startswith("http"):
        return None
    if any(marker in href for marker in _NON_RESULT_MARKERS) or href.lower().endswith(".pdf"):
        return None
    return href
