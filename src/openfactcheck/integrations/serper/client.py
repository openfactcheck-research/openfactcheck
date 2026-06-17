"""Async client for the Serper.dev API."""

import os
from collections.abc import Sequence
from typing import cast

import httpx

from openfactcheck.integrations.serper.errors import SerperConfigError, SerperRequestError
from openfactcheck.integrations.serper.params import SearchParams
from openfactcheck.integrations.serper.responses import ScrapeResponse, SearchResponse

DEFAULT_SEARCH_BASE_URL = "https://google.serper.dev"
"""Default base URL for the Serper search endpoints."""

DEFAULT_SCRAPE_BASE_URL = "https://scrape.serper.dev"
"""Default base URL for the Serper webpage scrape endpoint."""

DEFAULT_TIMEOUT = 30.0
"""Default per-request timeout in seconds."""


class SerperClient:
    """Async client for the Serper.dev Google Search API.

    Exposes the search and webpage-scrape endpoints as typed methods. The API
    key is read from the ``api_key`` argument or the ``SERPER_API_KEY``
    environment variable. New endpoints are cheap to add: route them through
    the shared request path.

    Example:
        ```python
        client = SerperClient()
        result = await client.search("who founded openai")
        for organic in result.organic:
            print(organic.title, organic.link)
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_SEARCH_BASE_URL,
        scrape_base_url: str = DEFAULT_SCRAPE_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        gl: str | None = None,
        hl: str | None = None,
    ) -> None:
        """Build a Serper client.

        Args:
            api_key: Serper API key. Falls back to the ``SERPER_API_KEY``
                environment variable when omitted.
            base_url: Base URL for the search endpoints.
            scrape_base_url: Base URL for the webpage scrape endpoint.
            timeout: Per-request timeout in seconds.
            gl: Default country code applied to bare-string searches.
            hl: Default language code applied to bare-string searches.

        Raises:
            SerperConfigError: No API key was given or found in the environment.
        """
        key = api_key if api_key is not None else os.environ.get("SERPER_API_KEY")
        if not key:
            raise SerperConfigError("no Serper API key; pass api_key= or set the SERPER_API_KEY environment variable.")
        self._api_key = key
        self._base_url = base_url.rstrip("/")
        self._scrape_base_url = scrape_base_url.rstrip("/")
        self._timeout = timeout
        self._gl = gl
        self._hl = hl

    async def search(self, query: str | SearchParams) -> SearchResponse:
        """Run a single web search.

        Args:
            query: A query string (using the client's default ``gl`` and
                ``hl``) or a fully specified [`SearchParams`][SearchParams].

        Returns:
            The parsed search response.

        Raises:
            SerperRequestError: The request failed or returned an error status.
        """
        data = await self._post(f"{self._base_url}/search", self._params_for(query).to_payload())
        return SearchResponse.model_validate(data)

    async def search_batch(self, queries: Sequence[str | SearchParams]) -> list[SearchResponse]:
        """Run several web searches in a single request.

        Args:
            queries: Query strings or [`SearchParams`][SearchParams] to search
                for together.

        Returns:
            One response per query, in the order given.

        Raises:
            SerperRequestError: The request failed, returned an error status, or
                did not return a list.
        """
        payload = [self._params_for(query).to_payload() for query in queries]
        data = await self._post(f"{self._base_url}/search", payload)
        if not isinstance(data, list):
            raise SerperRequestError("expected a list response for a batch search.")
        return [SearchResponse.model_validate(item) for item in cast("list[object]", data)]

    async def scrape(self, url: str, *, include_markdown: bool = False) -> ScrapeResponse:
        """Extract the contents of a web page.

        Args:
            url: The page to scrape.
            include_markdown: Whether to also return the page as Markdown.

        Returns:
            The page's extracted text, metadata, and optional Markdown.

        Raises:
            SerperRequestError: The request failed or returned an error status.
        """
        data = await self._post(self._scrape_base_url, {"url": url, "includeMarkdown": include_markdown})
        return ScrapeResponse.model_validate(data)

    def _params_for(self, query: str | SearchParams) -> SearchParams:
        """Coerce a query string or params into a [`SearchParams`][SearchParams]."""
        if isinstance(query, SearchParams):
            return query
        return SearchParams(q=query, gl=self._gl, hl=self._hl)

    async def _post(self, url: str, payload: object) -> object:
        """Send a POST request to ``url`` and return the decoded JSON body."""
        headers = {"X-API-KEY": self._api_key, "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise SerperRequestError(f"Serper request to {url} returned status {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise SerperRequestError(f"Serper request to {url} failed: {exc}.") from exc
