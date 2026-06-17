"""Tests for the SerperClient. httpx is faked at the request boundary."""

from typing import Any

import httpx
import pytest
from pytest_mock import MockerFixture

from openfactcheck.integrations.serper import SearchParams, SerperClient, SerperConfigError, SerperRequestError


class _FakeResponse:
    def __init__(self, json_data: object, *, status_error: bool = False) -> None:
        self._json = json_data
        self._status_error = status_error

    def raise_for_status(self) -> None:
        if self._status_error:
            request = httpx.Request("POST", "https://google.serper.dev/search")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    def json(self) -> object:
        return self._json


class _FakeAsyncClient:
    """Stand-in for httpx.AsyncClient that records the request and returns a fixed response."""

    def __init__(self, response: _FakeResponse, recorder: dict[str, Any]) -> None:
        self._response = response
        self._recorder = recorder

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False

    async def post(self, url: str, *, headers: dict[str, str] | None = None, json: object = None) -> _FakeResponse:
        self._recorder.update(url=url, headers=headers, json=json)
        return self._response


def _patch_httpx(mocker: MockerFixture, response: _FakeResponse) -> dict[str, Any]:
    recorder: dict[str, Any] = {}
    mocker.patch(
        "openfactcheck.integrations.serper.client.httpx.AsyncClient",
        lambda **_: _FakeAsyncClient(response, recorder),
    )
    return recorder


@pytest.mark.asyncio(loop_scope="function")
async def test_SerperClient_search_parses_response(mocker: MockerFixture) -> None:
    response = _FakeResponse({"organic": [{"title": "OpenAI", "link": "https://openai.com", "position": 1}]})
    _patch_httpx(mocker, response)
    client = SerperClient(api_key="test-key")

    result = await client.search("openai")

    assert result.organic[0].title == "OpenAI"
    assert result.organic[0].link == "https://openai.com"


@pytest.mark.asyncio(loop_scope="function")
async def test_SerperClient_search_sends_key_query_and_endpoint(mocker: MockerFixture) -> None:
    recorder = _patch_httpx(mocker, _FakeResponse({"organic": []}))
    client = SerperClient(api_key="test-key", gl="us")

    await client.search("openai")

    assert recorder["url"] == "https://google.serper.dev/search"
    assert recorder["headers"]["X-API-KEY"] == "test-key"
    assert recorder["json"] == {"q": "openai", "gl": "us"}


@pytest.mark.asyncio(loop_scope="function")
async def test_SerperClient_search_accepts_search_params(mocker: MockerFixture) -> None:
    recorder = _patch_httpx(mocker, _FakeResponse({"organic": []}))
    client = SerperClient(api_key="test-key")

    await client.search(SearchParams(q="openai", num=5, tbs="qdr:d"))

    assert recorder["json"] == {"q": "openai", "num": 5, "tbs": "qdr:d"}


@pytest.mark.asyncio(loop_scope="function")
async def test_SerperClient_search_batch_parses_list(mocker: MockerFixture) -> None:
    response = _FakeResponse([{"organic": [{"title": "a", "link": "u1"}]}, {"organic": [{"title": "b", "link": "u2"}]}])
    recorder = _patch_httpx(mocker, response)
    client = SerperClient(api_key="test-key")

    results = await client.search_batch(["a", "b"])

    assert [r.organic[0].title for r in results] == ["a", "b"]
    assert recorder["json"] == [{"q": "a"}, {"q": "b"}]


@pytest.mark.asyncio(loop_scope="function")
async def test_SerperClient_search_batch_rejects_non_list(mocker: MockerFixture) -> None:
    _patch_httpx(mocker, _FakeResponse({"organic": []}))
    client = SerperClient(api_key="test-key")

    with pytest.raises(SerperRequestError):
        await client.search_batch(["a"])


@pytest.mark.asyncio(loop_scope="function")
async def test_SerperClient_scrape_parses_and_targets_scrape_host(mocker: MockerFixture) -> None:
    recorder = _patch_httpx(mocker, _FakeResponse({"text": "hello", "markdown": "# hello"}))
    client = SerperClient(api_key="test-key")

    result = await client.scrape("https://example.com", include_markdown=True)

    assert result.text == "hello"
    assert recorder["url"] == "https://scrape.serper.dev"
    assert recorder["json"] == {"url": "https://example.com", "includeMarkdown": True}


@pytest.mark.asyncio(loop_scope="function")
async def test_SerperClient_wraps_http_error(mocker: MockerFixture) -> None:
    _patch_httpx(mocker, _FakeResponse({}, status_error=True))
    client = SerperClient(api_key="test-key")

    with pytest.raises(SerperRequestError):
        await client.search("openai")


def test_SerperClient_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERPER_API_KEY", raising=False)

    with pytest.raises(SerperConfigError):
        SerperClient()
