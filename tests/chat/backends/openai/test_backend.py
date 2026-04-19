"""Tests for OpenAIBackend with mocked openai SDK."""

from types import SimpleNamespace

import pytest

from openfactcheck.chat.backends.openai import OpenAIBackend
from openfactcheck.chat.config import OpenAIConfig, RuntimeConfig
from openfactcheck.chat.errors import AuthenticationError
from openfactcheck.chat.messages import UserMessage
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


def _patch_sync_client(mocker, response) -> object:  # noqa: ANN001
    """Mock the sync OpenAI client to return the given response."""
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=mocker.MagicMock(return_value=response)),
        ),
    )
    mock_cls = mocker.MagicMock(return_value=mock_client)
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_openai", return_value=mock_cls)
    return mock_client.chat.completions.create


def _patch_async_client(mocker, response, *, is_coro: bool = True):  # noqa: ANN001, ANN202
    """Mock the async OpenAI client to return the given response."""
    if is_coro:

        async def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
            return response
    else:

        def _create(**kwargs):  # noqa: ANN002, ANN003, ANN202, ARG001
            return response

    mock_create = mocker.MagicMock(side_effect=_create)
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=mock_create)),
    )
    mock_cls = mocker.MagicMock(return_value=mock_client)
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_async_openai", return_value=mock_cls)
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
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=mocker.MagicMock(side_effect=err)),
        ),
    )
    mock_cls = mocker.MagicMock(return_value=mock_client)
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_openai", return_value=mock_cls)
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
