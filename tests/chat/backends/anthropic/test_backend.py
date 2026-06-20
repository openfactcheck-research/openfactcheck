"""Tests for AnthropicBackend with mocked anthropic SDK."""

from types import SimpleNamespace

import pytest

from openfactcheck.chat.backends.anthropic import AnthropicBackend
from openfactcheck.chat.config import AnthropicConfig, RuntimeConfig
from openfactcheck.chat.errors import AuthenticationError
from openfactcheck.messages import SystemMessage, UserMessage
from openfactcheck.chat.requests import ChatRequest
from openfactcheck.chat.responses import FinishReason, StreamEnd, TextDelta


def _build_request(*, include_system: bool = False) -> ChatRequest:
    messages = [SystemMessage(content="You are terse.")] if include_system else []
    messages.append(UserMessage(content="Hi"))
    return ChatRequest(
        messages=messages,
        config=AnthropicConfig(model="claude-sonnet-4-6", max_output_tokens=100),
        runtime=RuntimeConfig(),
    )


def _fake_response() -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Hello!")],
        usage=SimpleNamespace(input_tokens=5, output_tokens=3),
        stop_reason="end_turn",
    )


def _fake_stream_events():  # noqa: ANN202
    """Sync iterable mimicking Anthropic's RawMessageStreamEvent union."""
    yield SimpleNamespace(
        type="message_start",
        message=SimpleNamespace(usage=SimpleNamespace(input_tokens=5)),
    )
    yield SimpleNamespace(
        type="content_block_delta",
        delta=SimpleNamespace(type="text_delta", text="Hello"),
    )
    yield SimpleNamespace(
        type="content_block_delta",
        delta=SimpleNamespace(type="text_delta", text=", world!"),
    )
    yield SimpleNamespace(
        type="message_delta",
        delta=SimpleNamespace(stop_reason="end_turn"),
        usage=SimpleNamespace(output_tokens=3),
    )
    yield SimpleNamespace(type="message_stop")


async def _fake_astream_events():  # noqa: ANN202
    """Async iterable of streaming events."""
    for event in _fake_stream_events():
        yield event


def _fake_client(mocker, create, *, is_async: bool = False):  # noqa: ANN001, ANN202
    """Wrap a ``create`` mock in a reusable, closable fake Anthropic client and its class.

    ``with_options`` returns the same client, mirroring the SDK sharing one pool
    across per-request views. ``close`` stands in for the SDK lifecycle method,
    which is a coroutine on the async client.
    """
    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    client.with_options = lambda **_: client
    client.close = mocker.AsyncMock() if is_async else mocker.MagicMock()
    cls = mocker.MagicMock(return_value=client)
    return cls, client


def _patch_sync_client(mocker, response) -> object:  # noqa: ANN001
    """Mock the sync Anthropic client to return the given response."""
    create = mocker.MagicMock(return_value=response)
    cls, _ = _fake_client(mocker, create)
    mocker.patch("openfactcheck.chat.backends.anthropic.backend.load_anthropic", return_value=cls)
    return create


def _patch_async_client(mocker, response, *, is_coro: bool = True):  # noqa: ANN001, ANN202
    """Mock the async Anthropic client to return the given response."""
    if is_coro:

        async def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
            return response
    else:

        def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
            return response

    mock_create = mocker.MagicMock(side_effect=_create)
    cls, _ = _fake_client(mocker, mock_create, is_async=True)
    mocker.patch("openfactcheck.chat.backends.anthropic.backend.load_async_anthropic", return_value=cls)
    return mock_create


# ---------------------------------------------------------------------------
# Sync: completion
# ---------------------------------------------------------------------------


def test_AnthropicBackend_completion_sync(mocker) -> None:  # noqa: ANN001
    """AnthropicBackend.completion calls the SDK and maps the response."""
    mock_create = _patch_sync_client(mocker, _fake_response())
    backend = AnthropicBackend()

    response = backend.completion(_build_request())

    assert response.message.content == "Hello!"
    assert response.finish_reason == FinishReason.STOP
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 100
    assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]
    assert "system" not in call_kwargs


def test_AnthropicBackend_completion_routes_system_prompt(mocker) -> None:  # noqa: ANN001
    """SystemMessage is passed via top-level system= kwarg, not inside messages."""
    mock_create = _patch_sync_client(mocker, _fake_response())
    backend = AnthropicBackend()

    backend.completion(_build_request(include_system=True))

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["system"] == "You are terse."
    assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]


def test_AnthropicBackend_completion_maps_errors_sync(mocker) -> None:  # noqa: ANN001
    """Sync completion translates Anthropic errors."""
    import httpx
    from anthropic import AuthenticationError as AnthropicAuth

    err = AnthropicAuth(
        message="bad key",
        response=httpx.Response(status_code=401, request=httpx.Request("POST", "https://api.anthropic.com")),
        body=None,
    )
    cls, _ = _fake_client(mocker, mocker.MagicMock(side_effect=err))
    mocker.patch("openfactcheck.chat.backends.anthropic.backend.load_anthropic", return_value=cls)
    backend = AnthropicBackend()

    with pytest.raises(AuthenticationError):
        backend.completion(_build_request())


# ---------------------------------------------------------------------------
# Async: acompletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="function")
async def test_AnthropicBackend_acompletion(mocker) -> None:  # noqa: ANN001
    """AnthropicBackend.acompletion calls the async SDK and maps the response."""
    mock_create = _patch_async_client(mocker, _fake_response())
    backend = AnthropicBackend()

    response = await backend.acompletion(_build_request())

    assert response.message.content == "Hello!"
    assert response.finish_reason == FinishReason.STOP
    mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# Sync: stream
# ---------------------------------------------------------------------------


def test_AnthropicBackend_stream_sync(mocker) -> None:  # noqa: ANN001
    """AnthropicBackend.stream yields TextDelta chunks and a final StreamEnd."""
    _patch_sync_client(mocker, _fake_stream_events())
    backend = AnthropicBackend()

    events = list(backend.stream(_build_request()))

    deltas = [e for e in events if isinstance(e, TextDelta)]
    ends = [e for e in events if isinstance(e, StreamEnd)]
    assert [d.content for d in deltas] == ["Hello", ", world!"]
    assert len(ends) == 1
    assert ends[0].finish_reason == FinishReason.STOP
    assert ends[0].usage is not None
    assert ends[0].usage.input_tokens == 5
    assert ends[0].usage.output_tokens == 3


# ---------------------------------------------------------------------------
# Async: astream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="function")
async def test_AnthropicBackend_astream_yields_events(mocker) -> None:  # noqa: ANN001
    """AnthropicBackend.astream yields TextDelta chunks and a final StreamEnd."""
    _patch_async_client(mocker, _fake_astream_events())
    backend = AnthropicBackend()

    events = [event async for event in backend.astream(_build_request())]

    deltas = [e for e in events if isinstance(e, TextDelta)]
    ends = [e for e in events if isinstance(e, StreamEnd)]
    assert [d.content for d in deltas] == ["Hello", ", world!"]
    assert len(ends) == 1
    assert ends[0].finish_reason == FinishReason.STOP
    assert ends[0].usage is not None
    assert ends[0].usage.output_tokens == 3


# ---------------------------------------------------------------------------
# Structured output: the forced tool's input JSON streams as text
# ---------------------------------------------------------------------------


def _fake_tool_stream_events():  # noqa: ANN202
    """Sync iterable mimicking a forced-tool-use (structured output) stream."""
    yield SimpleNamespace(type="message_start", message=SimpleNamespace(usage=SimpleNamespace(input_tokens=5)))
    yield SimpleNamespace(
        type="content_block_delta",
        delta=SimpleNamespace(type="input_json_delta", partial_json='{"name": "Ada"'),
    )
    yield SimpleNamespace(
        type="content_block_delta",
        delta=SimpleNamespace(type="input_json_delta", partial_json=', "age": 36}'),
    )
    yield SimpleNamespace(
        type="message_delta",
        delta=SimpleNamespace(stop_reason="tool_use"),
        usage=SimpleNamespace(output_tokens=7),
    )
    yield SimpleNamespace(type="message_stop")


async def _fake_tool_astream_events():  # noqa: ANN202
    """Async iterable of the structured-output stream events."""
    for event in _fake_tool_stream_events():
        yield event


def test_AnthropicBackend_stream_surfaces_tool_input_json(mocker) -> None:  # noqa: ANN001
    """Structured output streams the forced tool's input JSON as TextDelta chunks."""
    _patch_sync_client(mocker, _fake_tool_stream_events())
    backend = AnthropicBackend()

    events = list(backend.stream(_build_request()))

    deltas = [e for e in events if isinstance(e, TextDelta)]
    assert "".join(d.content for d in deltas) == '{"name": "Ada", "age": 36}'


@pytest.mark.asyncio(loop_scope="function")
async def test_AnthropicBackend_astream_surfaces_tool_input_json(mocker) -> None:  # noqa: ANN001
    """Structured output streams the forced tool's input JSON over the async iterator."""
    _patch_async_client(mocker, _fake_tool_astream_events())
    backend = AnthropicBackend()

    events = [event async for event in backend.astream(_build_request())]

    deltas = [e for e in events if isinstance(e, TextDelta)]
    assert "".join(d.content for d in deltas) == '{"name": "Ada", "age": 36}'


# ---------------------------------------------------------------------------
# Client reuse and lifecycle
# ---------------------------------------------------------------------------


def test_AnthropicBackend_reuses_one_sync_client(mocker) -> None:  # noqa: ANN001
    """The sync client is built once and reused across calls."""
    cls, _ = _fake_client(mocker, mocker.MagicMock(return_value=_fake_response()))
    mocker.patch("openfactcheck.chat.backends.anthropic.backend.load_anthropic", return_value=cls)
    backend = AnthropicBackend()

    backend.completion(_build_request())
    backend.completion(_build_request())

    assert cls.call_count == 1


def test_AnthropicBackend_close_releases_sync_client(mocker) -> None:  # noqa: ANN001
    """close shuts the sync client, is idempotent, and lets a later call rebuild it."""
    cls, client = _fake_client(mocker, mocker.MagicMock(return_value=_fake_response()))
    mocker.patch("openfactcheck.chat.backends.anthropic.backend.load_anthropic", return_value=cls)
    backend = AnthropicBackend()

    backend.completion(_build_request())
    backend.close()
    backend.close()
    backend.completion(_build_request())

    client.close.assert_called_once()
    assert cls.call_count == 2


@pytest.mark.asyncio(loop_scope="function")
async def test_AnthropicBackend_reuses_one_async_client(mocker) -> None:  # noqa: ANN001
    """The async client is built once and reused across calls."""

    async def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
        return _fake_response()

    cls, _ = _fake_client(mocker, mocker.MagicMock(side_effect=_create), is_async=True)
    mocker.patch("openfactcheck.chat.backends.anthropic.backend.load_async_anthropic", return_value=cls)
    backend = AnthropicBackend()

    await backend.acompletion(_build_request())
    await backend.acompletion(_build_request())

    assert cls.call_count == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_AnthropicBackend_aclose_releases_async_client(mocker) -> None:  # noqa: ANN001
    """aclose shuts the async client, is idempotent, and lets a later call rebuild it."""

    async def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
        return _fake_response()

    cls, client = _fake_client(mocker, mocker.MagicMock(side_effect=_create), is_async=True)
    mocker.patch("openfactcheck.chat.backends.anthropic.backend.load_async_anthropic", return_value=cls)
    backend = AnthropicBackend()

    await backend.acompletion(_build_request())
    await backend.aclose()
    await backend.aclose()
    await backend.acompletion(_build_request())

    client.close.assert_awaited_once()
    assert cls.call_count == 2
