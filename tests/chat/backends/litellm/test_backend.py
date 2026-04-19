"""Tests for LiteLLMBackend with mocked litellm."""

from types import SimpleNamespace

import pytest

from openfactcheck.chat.backends.litellm import LiteLLMBackend
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


# ---------------------------------------------------------------------------
# Sync: completion
# ---------------------------------------------------------------------------


def test_LiteLLMBackend_completion_sync(mocker) -> None:  # noqa: ANN001 - pytest-mock fixture.
    """LiteLLMBackend.completion calls litellm.completion and maps the response."""
    mock_completion = mocker.patch("litellm.completion", return_value=_fake_response())
    backend = LiteLLMBackend()

    response = backend.completion(_build_request())

    assert response.message.content == "Hello!"
    assert response.finish_reason == FinishReason.STOP
    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["model"] == "openai/gpt-4o"
    assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]


def test_LiteLLMBackend_completion_maps_errors_sync(mocker) -> None:  # noqa: ANN001 - pytest-mock fixture.
    """Sync completion translates litellm errors."""
    from litellm.exceptions import AuthenticationError as LitellmAuth  # noqa: PLC0415

    mocker.patch(
        "litellm.completion",
        side_effect=LitellmAuth(message="bad key", llm_provider="openai", model="gpt-4o"),
    )
    backend = LiteLLMBackend()

    with pytest.raises(AuthenticationError):
        backend.completion(_build_request())


# ---------------------------------------------------------------------------
# Async: acompletion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="function")
async def test_LiteLLMBackend_acompletion(mocker) -> None:  # noqa: ANN001 - pytest-mock fixture.
    """LiteLLMBackend.acompletion calls litellm.acompletion and maps the response."""
    mock_acompletion = mocker.patch("litellm.acompletion", return_value=_fake_response())
    backend = LiteLLMBackend()

    response = await backend.acompletion(_build_request())

    assert response.message.content == "Hello!"
    assert response.finish_reason == FinishReason.STOP
    mock_acompletion.assert_called_once()


@pytest.mark.asyncio(loop_scope="function")
async def test_LiteLLMBackend_acompletion_maps_errors(mocker) -> None:  # noqa: ANN001 - pytest-mock fixture.
    """Async acompletion translates litellm errors."""
    from litellm.exceptions import AuthenticationError as LitellmAuth  # noqa: PLC0415

    mocker.patch(
        "litellm.acompletion",
        side_effect=LitellmAuth(message="bad key", llm_provider="openai", model="gpt-4o"),
    )
    backend = LiteLLMBackend()

    with pytest.raises(AuthenticationError):
        await backend.acompletion(_build_request())


# ---------------------------------------------------------------------------
# Sync: stream
# ---------------------------------------------------------------------------


def test_LiteLLMBackend_stream_sync(mocker) -> None:  # noqa: ANN001 - pytest-mock fixture.
    """LiteLLMBackend.stream yields TextDelta chunks and a final StreamEnd."""
    mocker.patch("litellm.completion", return_value=_fake_stream_chunks())
    backend = LiteLLMBackend()

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
async def test_LiteLLMBackend_astream_yields_events(mocker) -> None:  # noqa: ANN001 - pytest-mock fixture.
    """LiteLLMBackend.astream yields TextDelta chunks and a final StreamEnd."""
    mocker.patch("litellm.acompletion", return_value=_fake_astream_chunks())
    backend = LiteLLMBackend()

    events = [event async for event in backend.astream(_build_request())]

    deltas = [e for e in events if isinstance(e, TextDelta)]
    ends = [e for e in events if isinstance(e, StreamEnd)]
    assert [d.content for d in deltas] == ["Hello", ", world!"]
    assert len(ends) == 1
    assert ends[0].finish_reason == FinishReason.STOP
    assert ends[0].usage is not None
    assert ends[0].usage.output_tokens == 3
