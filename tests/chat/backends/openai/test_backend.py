"""Tests for OpenAIBackend with mocked openai SDK."""

from types import SimpleNamespace

import pytest

from openfactcheck.chat.backends.openai import OpenAIBackend
from openfactcheck.chat.config import OpenAIConfig, RuntimeConfig
from openfactcheck.chat.errors import AuthenticationError
from openfactcheck.messages import UserMessage
from openfactcheck.chat.requests import ChatRequest
from openfactcheck.chat.responses import FinishReason, StreamEnd, TextDelta


def _build_request() -> ChatRequest:
    return ChatRequest(
        messages=[UserMessage(content="Hi")],
        config=OpenAIConfig(model="gpt-4o"),
        runtime=RuntimeConfig(),
    )


def _fake_response() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Hello!", tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
    )


def _fake_stream_chunks():  # noqa: ANN202
    """Sync iterable of streaming chunks."""
    yield SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello"), finish_reason=None)],
        usage=None,
    )
    yield SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=", world!"), finish_reason=None)],
        usage=None,
    )
    yield SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=None), finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
    )


async def _fake_astream_chunks():  # noqa: ANN202
    """Async iterable of streaming chunks."""
    for chunk in _fake_stream_chunks():
        yield chunk


def _fake_client(mocker, create, *, is_async: bool = False):  # noqa: ANN001, ANN202
    """Wrap a ``create`` mock in a reusable, closable fake OpenAI client and its class.

    ``with_options`` returns the same client, mirroring the SDK sharing one pool
    across per-request views. ``close`` stands in for the SDK lifecycle method,
    which is a coroutine on the async client.
    """
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    client.with_options = lambda **_: client
    client.close = mocker.AsyncMock() if is_async else mocker.MagicMock()
    cls = mocker.MagicMock(return_value=client)
    return cls, client


def _patch_sync_client(mocker, response) -> object:  # noqa: ANN001
    """Mock the sync OpenAI client to return the given response."""
    create = mocker.MagicMock(return_value=response)
    cls, _ = _fake_client(mocker, create)
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_openai", return_value=cls)
    return create


def _patch_async_client(mocker, response, *, is_coro: bool = True):  # noqa: ANN001, ANN202
    """Mock the async OpenAI client to return the given response."""
    if is_coro:

        async def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
            return response
    else:

        def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
            return response

    mock_create = mocker.MagicMock(side_effect=_create)
    cls, _ = _fake_client(mocker, mock_create, is_async=True)
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_async_openai", return_value=cls)
    return mock_create


# ---------------------------------------------------------------------------
# Sync: completion
# ---------------------------------------------------------------------------


def test_OpenAIBackend_completion_sync(mocker) -> None:  # noqa: ANN001
    """OpenAIBackend.completion calls the SDK and maps the response."""
    mock_create = _patch_sync_client(mocker, _fake_response())
    backend = OpenAIBackend()

    response = backend.completion(_build_request())

    assert response.message.content == "Hello!"
    assert response.finish_reason == FinishReason.STOP
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]


def test_OpenAIBackend_completion_maps_errors_sync(mocker) -> None:  # noqa: ANN001
    """Sync completion translates OpenAI errors."""
    import httpx
    from openai import AuthenticationError as OpenAIAuth

    err = OpenAIAuth(
        message="bad key",
        response=httpx.Response(status_code=401, request=httpx.Request("POST", "https://api.openai.com")),
        body=None,
    )
    cls, _ = _fake_client(mocker, mocker.MagicMock(side_effect=err))
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_openai", return_value=cls)
    backend = OpenAIBackend()

    with pytest.raises(AuthenticationError):
        backend.completion(_build_request())


# ---------------------------------------------------------------------------
# Async: acompletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="function")
async def test_OpenAIBackend_acompletion(mocker) -> None:  # noqa: ANN001
    """OpenAIBackend.acompletion calls the async SDK and maps the response."""
    mock_create = _patch_async_client(mocker, _fake_response())
    backend = OpenAIBackend()

    response = await backend.acompletion(_build_request())

    assert response.message.content == "Hello!"
    assert response.finish_reason == FinishReason.STOP
    mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# Sync: stream
# ---------------------------------------------------------------------------


def test_OpenAIBackend_stream_sync(mocker) -> None:  # noqa: ANN001
    """OpenAIBackend.stream yields TextDelta chunks and a final StreamEnd."""
    _patch_sync_client(mocker, _fake_stream_chunks())
    backend = OpenAIBackend()

    events = list(backend.stream(_build_request()))

    deltas = [e for e in events if isinstance(e, TextDelta)]
    ends = [e for e in events if isinstance(e, StreamEnd)]
    assert [d.content for d in deltas] == ["Hello", ", world!"]
    assert len(ends) == 1
    assert ends[0].finish_reason == FinishReason.STOP


# ---------------------------------------------------------------------------
# Async: astream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="function")
async def test_OpenAIBackend_astream_yields_events(mocker) -> None:  # noqa: ANN001
    """OpenAIBackend.astream yields TextDelta chunks and a final StreamEnd."""
    _patch_async_client(mocker, _fake_astream_chunks())
    backend = OpenAIBackend()

    events = [event async for event in backend.astream(_build_request())]

    deltas = [e for e in events if isinstance(e, TextDelta)]
    ends = [e for e in events if isinstance(e, StreamEnd)]
    assert [d.content for d in deltas] == ["Hello", ", world!"]
    assert len(ends) == 1
    assert ends[0].finish_reason == FinishReason.STOP
    assert ends[0].usage is not None
    assert ends[0].usage.output_tokens == 3


# ---------------------------------------------------------------------------
# Client reuse and lifecycle
# ---------------------------------------------------------------------------


def test_OpenAIBackend_reuses_one_sync_client(mocker) -> None:  # noqa: ANN001
    """The sync client is built once and reused across calls."""
    cls, _ = _fake_client(mocker, mocker.MagicMock(return_value=_fake_response()))
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_openai", return_value=cls)
    backend = OpenAIBackend()

    backend.completion(_build_request())
    backend.completion(_build_request())

    assert cls.call_count == 1


def test_OpenAIBackend_close_releases_sync_client(mocker) -> None:  # noqa: ANN001
    """close shuts the sync client, is idempotent, and lets a later call rebuild it."""
    cls, client = _fake_client(mocker, mocker.MagicMock(return_value=_fake_response()))
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_openai", return_value=cls)
    backend = OpenAIBackend()

    backend.completion(_build_request())
    backend.close()
    backend.close()
    backend.completion(_build_request())

    client.close.assert_called_once()
    assert cls.call_count == 2


@pytest.mark.asyncio(loop_scope="function")
async def test_OpenAIBackend_reuses_one_async_client(mocker) -> None:  # noqa: ANN001
    """The async client is built once and reused across calls."""

    async def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
        return _fake_response()

    cls, _ = _fake_client(mocker, mocker.MagicMock(side_effect=_create), is_async=True)
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_async_openai", return_value=cls)
    backend = OpenAIBackend()

    await backend.acompletion(_build_request())
    await backend.acompletion(_build_request())

    assert cls.call_count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_OpenAIBackend_aclose_releases_async_client(mocker) -> None:  # noqa: ANN001
    """aclose shuts the async client, is idempotent, and lets a later call rebuild it."""

    async def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
        return _fake_response()

    cls, client = _fake_client(mocker, mocker.MagicMock(side_effect=_create), is_async=True)
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_async_openai", return_value=cls)
    backend = OpenAIBackend()

    await backend.acompletion(_build_request())
    await backend.aclose()
    await backend.aclose()
    await backend.acompletion(_build_request())

    client.close.assert_awaited_once()
    assert cls.call_count == 2
