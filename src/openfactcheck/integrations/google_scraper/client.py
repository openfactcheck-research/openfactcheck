"""Async client that retrieves web evidence by scraping Google.

Replicates the FactcheckGPT retrieval method: search Google, scrape the result
pages, split them into overlapping passages, and rerank the passages against the
query with a cross-encoder. No search API or key is involved; results come from
parsing Google's results page directly, so retrieval is best-effort and Google
may rate-limit or block automated requests.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx

from openfactcheck.integrations.google_scraper.errors import GoogleScraperRequestError
from openfactcheck.integrations.google_scraper.imports import load_cross_encoder
from openfactcheck.integrations.google_scraper.parse import (
    chunk_passages,
    extract_result_urls,
    extract_visible_text,
)
from openfactcheck.integrations.google_scraper.responses import Passage

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

GOOGLE_SEARCH_URL = "https://www.google.com/search"
"""Endpoint whose results page the client parses for organic URLs."""

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0"
"""Desktop user agent; Google serves a parseable results page to desktop agents."""

DEFAULT_TIMEOUT = 10.0
"""Default per-request timeout in seconds."""

DEFAULT_NUM_RESULTS = 5
"""Default number of search result pages to scrape per query."""

DEFAULT_SENTENCES_PER_PASSAGE = 5
"""Default passage window size, in sentences."""

DEFAULT_SLIDING_DISTANCE = 2
"""Default number of sentences to advance between passages."""

DEFAULT_TOP_K = 5
"""Default number of reranked passages to return per query."""

DEFAULT_RANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
"""Default cross-encoder used to rerank passages against the query."""


class GoogleScraperClient:
    """Async client that retrieves web evidence by scraping Google search results.

    Searches Google, scrapes the result pages, chunks them into passages, and
    reranks those passages against the query with a cross-encoder. Needs the
    ``factcheckgpt`` extra (``beautifulsoup4`` and ``sentence-transformers``),
    which is imported on first use.

    Example:
        ```python
        client = GoogleScraperClient()
        passages = await client.retrieve("who founded openai")
        for passage in passages:
            print(passage.score, passage.url)
        ```
    """

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        num_results: int = DEFAULT_NUM_RESULTS,
        sentences_per_passage: int = DEFAULT_SENTENCES_PER_PASSAGE,
        sliding_distance: int = DEFAULT_SLIDING_DISTANCE,
        top_k: int = DEFAULT_TOP_K,
        ranker_model: str = DEFAULT_RANKER_MODEL,
        lang: str = "en",
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        """Build a Google scraper client.

        Args:
            timeout: Per-request timeout in seconds.
            num_results: How many search result pages to scrape per query.
            sentences_per_passage: Passage window size, in sentences.
            sliding_distance: Sentences to advance between passages.
            top_k: How many reranked passages to return per query.
            ranker_model: Cross-encoder model id used to rerank passages.
            lang: Interface and result language code, such as ``en``.
            user_agent: User agent sent with every request.
        """
        self._timeout = timeout
        self._num_results = num_results
        self._sentences_per_passage = sentences_per_passage
        self._sliding_distance = sliding_distance
        self._top_k = top_k
        self._ranker_name = ranker_model
        self._lang = lang
        self._user_agent = user_agent
        self._ranker: CrossEncoder | None = None

    async def search(self, query: str) -> list[str]:
        """Return the organic result URLs Google shows for a query.

        Args:
            query: The search query.

        Returns:
            Result URLs in rank order, capped at ``num_results``.

        Raises:
            GoogleScraperRequestError: The search request failed or was blocked.
        """
        async with self._http() as http:
            return await self._search(http, query)

    async def scrape(self, url: str) -> str | None:
        """Return the visible text of a page, or ``None`` when it cannot be read.

        Args:
            url: The page to scrape.

        Returns:
            The page's visible text, or ``None`` for a non-HTML or unreachable page.
        """
        async with self._http() as http:
            return await self._scrape(http, url)

    async def retrieve(self, query: str) -> list[Passage]:
        """Retrieve and rerank web passages relevant to a query.

        Searches Google, scrapes each result page, splits the pages into
        passages, and returns the passages most relevant to the query.

        Args:
            query: The query to find evidence for.

        Returns:
            The top reranked passages, highest score first; empty when nothing
            could be scraped.

        Raises:
            GoogleScraperRequestError: The search request failed or was blocked.
            GoogleScraperConfigError: The ``factcheckgpt`` extra is not installed.
        """
        async with self._http() as http:
            urls = await self._search(http, query)
            texts = await asyncio.gather(*(self._scrape(http, url) for url in urls))

        candidates = [
            (passage, url)
            for url, text in zip(urls, texts, strict=True)
            if text
            for passage in chunk_passages(
                text,
                sentences_per_passage=self._sentences_per_passage,
                sliding_distance=self._sliding_distance,
            )
        ]
        if not candidates:
            return []

        ranked = await asyncio.to_thread(self._rerank, query, candidates)
        return [Passage(text=text, url=url, score=score) for text, url, score in ranked[: self._top_k]]

    def _http(self) -> httpx.AsyncClient:
        """Build an HTTP client carrying the configured timeout and user agent."""
        return httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": self._user_agent},
            follow_redirects=True,
        )

    async def _search(self, http: httpx.AsyncClient, query: str) -> list[str]:
        """Run the search request and parse organic result URLs from the page."""
        params = {
            "q": query,
            "num": max(10, self._num_results * 2),
            "hl": self._lang,
            "lr": f"lang_{self._lang}",
        }
        try:
            response = await http.get(GOOGLE_SEARCH_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GoogleScraperRequestError(f"Google search for {query!r} failed: {exc}.") from exc
        return extract_result_urls(response.text, limit=self._num_results)

    async def _scrape(self, http: httpx.AsyncClient, url: str) -> str | None:
        """Fetch one page and return its visible text, or ``None`` on any failure.

        A single unreachable or non-HTML page is skipped rather than failing the
        whole retrieval.
        """
        try:
            response = await http.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        if "html" not in response.headers.get("content-type", ""):
            return None
        return extract_visible_text(response.text) or None

    def _rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[tuple[str, str, float]]:
        """Score each ``(passage, url)`` against the query and sort by score, descending."""
        ranker = self._load_ranker()
        scores = ranker.predict([(query, passage) for passage, _ in candidates])
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda item: item[1], reverse=True)
        return [(passage, url, float(score)) for (passage, url), score in ranked]

    def _load_ranker(self) -> CrossEncoder:
        """Build the cross-encoder once and reuse it across calls."""
        if self._ranker is None:
            self._ranker = load_cross_encoder()(self._ranker_name, max_length=512)
        return self._ranker
