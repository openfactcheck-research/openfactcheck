"""Tests for GoogleScraperClient. httpx, the parser, and the reranker are faked."""

import importlib.util

import httpx
import pytest
from pytest_mock import MockerFixture

from openfactcheck.integrations.google_scraper import (
    GoogleScraperClient,
    GoogleScraperConfigError,
    GoogleScraperRequestError,
    Passage,
)
from openfactcheck.integrations.google_scraper.client import GOOGLE_SEARCH_URL

_CLIENT = "openfactcheck.integrations.google_scraper.client"


class _FakeResponse:
    def __init__(self, *, content_type: str = "text/html", status_error: bool = False) -> None:
        self.text = "<html></html>"
        self.headers = {"content-type": content_type}
        self._status_error = status_error

    def raise_for_status(self) -> None:
        if self._status_error:
            request = httpx.Request("GET", "https://example.com")
            raise httpx.HTTPStatusError("error", request=request, response=httpx.Response(503, request=request))


class _FakeAsyncClient:
    def __init__(self, handler: object) -> None:
        self._handler = handler
        self.gets: list[tuple[str, object]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False

    async def get(self, url: str, *, params: object = None) -> _FakeResponse:
        self.gets.append((url, params))
        return self._handler(url)  # type: ignore[operator]


def _patch_httpx(mocker: MockerFixture, handler: object) -> list[_FakeAsyncClient]:
    created: list[_FakeAsyncClient] = []

    def _factory(**_: object) -> _FakeAsyncClient:
        client = _FakeAsyncClient(handler)
        created.append(client)
        return client

    mocker.patch(f"{_CLIENT}.httpx.AsyncClient", _factory)
    return created


class _FakeRanker:
    def __init__(self, *_: object, **__: object) -> None: ...

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        # Score by passage length, so reranking is deterministic in tests.
        return [float(len(passage)) for _query, passage in pairs]


@pytest.mark.asyncio(loop_scope="function")
async def test_GoogleScraperClient_retrieve_ranks_passages(mocker: MockerFixture) -> None:
    mocker.patch(f"{_CLIENT}.extract_result_urls", return_value=["https://a.com"])
    mocker.patch(f"{_CLIENT}.extract_visible_text", return_value="Short. A much longer sentence here. Mid one.")
    mocker.patch(f"{_CLIENT}.load_cross_encoder", return_value=_FakeRanker)
    _patch_httpx(mocker, lambda _url: _FakeResponse())
    client = GoogleScraperClient(top_k=2, sentences_per_passage=1, sliding_distance=1)

    passages = await client.retrieve("who")

    assert all(isinstance(passage, Passage) for passage in passages)
    assert len(passages) == 2  # noqa: PLR2004 - top_k.
    assert passages[0].score >= passages[1].score
    assert passages[0].url == "https://a.com"


@pytest.mark.asyncio(loop_scope="function")
async def test_GoogleScraperClient_retrieve_empty_when_no_results(mocker: MockerFixture) -> None:
    mocker.patch(f"{_CLIENT}.extract_result_urls", return_value=[])
    _patch_httpx(mocker, lambda _url: _FakeResponse())
    client = GoogleScraperClient()

    assert await client.retrieve("q") == []


@pytest.mark.asyncio(loop_scope="function")
async def test_GoogleScraperClient_search_targets_google(mocker: MockerFixture) -> None:
    mocker.patch(f"{_CLIENT}.extract_result_urls", return_value=["https://a.com"])
    created = _patch_httpx(mocker, lambda _url: _FakeResponse())
    client = GoogleScraperClient()

    urls = await client.search("openai")

    assert urls == ["https://a.com"]
    url, params = created[0].gets[0]
    assert url == GOOGLE_SEARCH_URL
    assert params["q"] == "openai"  # type: ignore[index]


@pytest.mark.asyncio(loop_scope="function")
async def test_GoogleScraperClient_search_wraps_http_error(mocker: MockerFixture) -> None:
    _patch_httpx(mocker, lambda _url: _FakeResponse(status_error=True))
    client = GoogleScraperClient()

    with pytest.raises(GoogleScraperRequestError):
        await client.search("openai")


@pytest.mark.asyncio(loop_scope="function")
async def test_GoogleScraperClient_scrape_skips_non_html(mocker: MockerFixture) -> None:
    _patch_httpx(mocker, lambda _url: _FakeResponse(content_type="application/pdf"))
    client = GoogleScraperClient()

    assert await client.scrape("https://example.com/doc.pdf") is None


@pytest.mark.asyncio(loop_scope="function")
async def test_GoogleScraperClient_scrape_returns_none_on_error(mocker: MockerFixture) -> None:
    _patch_httpx(mocker, lambda _url: _FakeResponse(status_error=True))
    client = GoogleScraperClient()

    assert await client.scrape("https://example.com") is None


def test_load_cross_encoder_raises_without_dependency() -> None:
    if importlib.util.find_spec("sentence_transformers") is not None:
        pytest.skip("sentence-transformers is installed")
    from openfactcheck.integrations.google_scraper.imports import load_cross_encoder

    with pytest.raises(GoogleScraperConfigError):
        load_cross_encoder()
