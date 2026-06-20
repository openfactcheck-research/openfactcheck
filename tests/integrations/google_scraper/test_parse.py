"""Tests for the Google scraper parsing helpers."""

import pytest

from openfactcheck.integrations.google_scraper.parse import (
    chunk_passages,
    extract_result_urls,
    extract_visible_text,
)


def test_chunk_passages_windows_over_sentences() -> None:
    text = "One here. Two here. Three here. Four here. Five here. Six here."

    passages = chunk_passages(text, sentences_per_passage=3, sliding_distance=2)

    assert passages[0] == "One here. Two here. Three here."
    # The window advances by the sliding distance.
    assert passages[1] == "Three here. Four here. Five here."


def test_chunk_passages_drops_overlong_sentences() -> None:
    long_sentence = "x" * 300
    text = f"Short one. {long_sentence}. Short two."

    passages = chunk_passages(text, sentences_per_passage=5, sliding_distance=5, max_sentence_chars=250)

    joined = " ".join(passages)
    assert "Short one." in joined
    assert "Short two." in joined
    assert long_sentence not in joined


def test_chunk_passages_empty_text() -> None:
    assert chunk_passages("", sentences_per_passage=5, sliding_distance=2) == []


# The HTML helpers call beautifulsoup4, which ships in the factcheckgpt extra.


def test_extract_result_urls_resolves_and_filters() -> None:
    pytest.importorskip("bs4")
    html = """
    <a href="/url?q=https://example.com/page&sa=U">result</a>
    <a href="https://news.example.org/story">direct</a>
    <a href="/search?q=more">google nav</a>
    <a href="https://www.google.com/preferences">settings</a>
    <a href="https://example.com/doc.pdf">a pdf</a>
    """

    urls = extract_result_urls(html, limit=10)

    assert urls == ["https://example.com/page", "https://news.example.org/story"]


def test_extract_result_urls_respects_limit() -> None:
    pytest.importorskip("bs4")
    html = '<a href="https://a.com">a</a><a href="https://b.com">b</a><a href="https://c.com">c</a>'

    assert extract_result_urls(html, limit=2) == ["https://a.com", "https://b.com"]


def test_extract_visible_text_drops_scripts_and_collapses_whitespace() -> None:
    pytest.importorskip("bs4")
    html = "<html><head><title>T</title></head><body><script>ignore()</script><p>Hello    world</p></body></html>"

    assert extract_visible_text(html) == "Hello world"
