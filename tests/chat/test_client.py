"""Tests for ChatClient with mocked backend."""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from openfactcheck.chat.backends.anthropic import AnthropicBackend
from openfactcheck.chat.backends.openai import OpenAIBackend
from openfactcheck.chat.client import ChatClient
from openfactcheck.chat.config import AnthropicConfig, OpenAIConfig, RuntimeConfig
from openfactcheck.chat.errors import StructuredOutputError, UnsupportedFeatureError
from openfactcheck.messages import AssistantMessage, UserMessage
from openfactcheck.chat.requests import ChatRequest
from openfactcheck.chat.responses import ChatResponse, FinishReason, StreamEnd, TextDelta, Usage


class _Person(BaseModel):
    name: str
    age: int


class ScriptedBackend:
    """Backend test double that returns a scripted sequence of reply contents."""

    def __init__(self, contents: list[str]) -> None:
        self._contents = contents
        self.requests: list[ChatRequest] = []

    def _next(self, request: ChatRequest) -> ChatResponse:
        content = self._contents[len(self.requests)]
        self.requests.append(request)
        return ChatResponse(message=AssistantMessage(content=content), model="gpt-4o", provider="openai")

    def completion(self, request: ChatRequest) -> ChatResponse:
        return self._next(request)

    async def acompletion(self, request: ChatRequest) -> ChatResponse:
        return self._next(request)


class FakeBackend:
    """Minimal backend for testing — implements all 4 protocol methods."""

    def __init__(self, response: ChatResponse) -> None:
        self.response = response
        self.last_request: ChatRequest | None = None

    def completion(self, request):  # noqa: ANN001, ANN201 - test double.
        self.last_request = request
        return self.response

    async def acompletion(self, request):  # noqa: ANN001, ANN201 - test double.
        self.last_request = request
        return self.response

    def stream(self, request):  # noqa: ANN001, ANN201 - test double.
        self.last_request = request
        yield TextDelta(content="Hello")
        yield TextDelta(content=", world!")
        yield StreamEnd(finish_reason=FinishReason.STOP, usage=Usage(input_tokens=5, output_tokens=3))

    async def astream(self, request):  # noqa: ANN001, ANN201 - test double.
        self.last_request = request
        yield TextDelta(content="Hello")
        yield TextDelta(content=", world!")
        yield StreamEnd(finish_reason=FinishReason.STOP, usage=Usage(input_tokens=5, output_tokens=3))


@pytest.fixture()
def fake_response() -> ChatResponse:
    """A canned ChatResponse for testing."""
    return ChatResponse(
        message=AssistantMessage(content="Hello!"),
        model="gpt-4o",
        provider="openai",
        usage=Usage(input_tokens=5, output_tokens=3),
        finish_reason=FinishReason.STOP,
    )


@pytest.fixture()
def openai_config() -> OpenAIConfig:
    """Minimal OpenAI config."""
    return OpenAIConfig(model="gpt-4o")


def test_ChatClient_completion_sync(fake_response: ChatResponse, openai_config: OpenAIConfig) -> None:
    """ChatClient.completion delegates synchronously."""
    backend = FakeBackend(fake_response)
    client = ChatClient(config=openai_config, backend=backend)  # type: ignore[arg-type]
    messages = [UserMessage(content="Hi")]

    result = client.completion(messages)

    assert result.message.content == "Hello!"
    assert backend.last_request is not None
    assert backend.last_request.messages == messages


@pytest.mark.asyncio(loop_scope="function")
async def test_ChatClient_acompletion(fake_response: ChatResponse, openai_config: OpenAIConfig) -> None:
    """ChatClient.acompletion delegates asynchronously."""
    backend = FakeBackend(fake_response)
    client = ChatClient(config=openai_config, backend=backend)  # type: ignore[arg-type]
    messages = [UserMessage(content="Hi")]

    result = await client.acompletion(messages)

    assert result.message.content == "Hello!"
    assert backend.last_request is not None
    assert backend.last_request.messages == messages
    assert backend.last_request.config is openai_config


@pytest.mark.asyncio(loop_scope="function")
async def test_ChatClient_acompletion_with_runtime(fake_response: ChatResponse, openai_config: OpenAIConfig) -> None:
    """ChatClient passes runtime through the ChatRequest."""
    backend = FakeBackend(fake_response)
    runtime = RuntimeConfig(timeout=30.0, max_retries=5)
    client = ChatClient(config=openai_config, runtime=runtime, backend=backend)  # type: ignore[arg-type]

    await client.acompletion([UserMessage(content="Hi")])

    assert backend.last_request is not None
    assert backend.last_request.runtime is runtime


def test_ChatClient_stream_sync(fake_response: ChatResponse, openai_config: OpenAIConfig) -> None:
    """ChatClient.stream yields typed events synchronously."""
    backend = FakeBackend(fake_response)
    client = ChatClient(config=openai_config, backend=backend)  # type: ignore[arg-type]

    events = list(client.stream([UserMessage(content="Hi")]))

    assert len(events) == 3
    assert isinstance(events[0], TextDelta)
    assert events[0].content == "Hello"
    assert isinstance(events[2], StreamEnd)
    assert events[2].finish_reason == FinishReason.STOP


@pytest.mark.asyncio(loop_scope="function")
async def test_ChatClient_astream_yields_events(fake_response: ChatResponse, openai_config: OpenAIConfig) -> None:
    """ChatClient.astream yields typed events asynchronously."""
    backend = FakeBackend(fake_response)
    client = ChatClient(config=openai_config, backend=backend)  # type: ignore[arg-type]

    events = [event async for event in client.astream([UserMessage(content="Hi")])]

    assert len(events) == 3
    assert isinstance(events[0], TextDelta)
    assert events[0].content == "Hello"
    assert isinstance(events[2], StreamEnd)
    assert events[2].usage is not None
    assert events[2].usage.output_tokens == 3


def test_ChatClient_default_runtime(openai_config: OpenAIConfig, fake_response: ChatResponse) -> None:
    """ChatClient creates default RuntimeConfig when none provided."""
    backend = FakeBackend(fake_response)

    client = ChatClient(config=openai_config, backend=backend)  # type: ignore[arg-type]

    assert client._runtime.max_retries == 2
    assert client._runtime.timeout is None


def test_ChatClient_default_backend_openai_uses_direct_sdk(openai_config: OpenAIConfig) -> None:
    """With no explicit backend, OpenAI configs resolve to the direct OpenAI SDK backend."""
    client = ChatClient(config=openai_config)

    assert isinstance(client._backend, OpenAIBackend)


def test_ChatClient_default_backend_anthropic_uses_direct_sdk() -> None:
    """With no explicit backend, Anthropic configs resolve to the direct Anthropic SDK backend."""
    config = AnthropicConfig(model="claude-sonnet-4-6", max_output_tokens=200)

    client = ChatClient(config=config)

    assert isinstance(client._backend, AnthropicBackend)


def test_ChatClient_completion_as_returns_model(openai_config: OpenAIConfig) -> None:
    """completion_as validates the reply into the requested model and sets a response_format."""
    backend = ScriptedBackend(['{"name": "Ada", "age": 36}'])
    client = ChatClient(config=openai_config, backend=backend)  # type: ignore[arg-type]

    person = client.completion_as([UserMessage(content="Make a person")], _Person)

    assert person == _Person(name="Ada", age=36)
    assert backend.requests[0].response_format is not None
    assert backend.requests[0].response_format.name == "_Person"


@pytest.mark.asyncio(loop_scope="function")
async def test_ChatClient_acompletion_as_returns_model(openai_config: OpenAIConfig) -> None:
    """acompletion_as validates the reply into the requested model."""
    backend = ScriptedBackend(['{"name": "Ada", "age": 36}'])
    client = ChatClient(config=openai_config, backend=backend)  # type: ignore[arg-type]

    person = await client.acompletion_as([UserMessage(content="Make a person")], _Person)

    assert person == _Person(name="Ada", age=36)


def test_ChatClient_completion_as_raises_on_invalid(openai_config: OpenAIConfig) -> None:
    """With max_parse_retries=0, an invalid reply raises StructuredOutputError without retrying."""
    backend = ScriptedBackend(['{"name": "Ada"}'])
    client = ChatClient(config=openai_config, runtime=RuntimeConfig(max_parse_retries=0), backend=backend)  # type: ignore[arg-type]

    with pytest.raises(StructuredOutputError) as excinfo:
        client.completion_as([UserMessage(content="Make a person")], _Person)

    assert len(backend.requests) == 1
    assert excinfo.value.raw == '{"name": "Ada"}'


def test_ChatClient_completion_as_retries_then_succeeds(openai_config: OpenAIConfig) -> None:
    """A validation failure is reprompted, and the retried reply is returned."""
    backend = ScriptedBackend(['{"name": "Ada"}', '{"name": "Ada", "age": 36}'])
    client = ChatClient(config=openai_config, runtime=RuntimeConfig(max_parse_retries=2), backend=backend)  # type: ignore[arg-type]

    person = client.completion_as([UserMessage(content="Make a person")], _Person)

    assert person == _Person(name="Ada", age=36)
    assert len(backend.requests) == 2
    # The retry carries the original turn plus the failed reply and a reprompt.
    assert len(backend.requests[1].messages) == 3
    assert isinstance(backend.requests[1].messages[-1], UserMessage)


def test_ChatClient_completion_as_unsupported_raises(openai_config: OpenAIConfig, mocker) -> None:  # noqa: ANN001 - pytest-mock fixture.
    """completion_as raises when the provider does not support structured output."""
    backend = ScriptedBackend(['{"name": "Ada", "age": 36}'])
    client = ChatClient(config=openai_config, backend=backend)  # type: ignore[arg-type]
    mocker.patch.object(client._provider, "capabilities", SimpleNamespace(structured_output=False))

    with pytest.raises(UnsupportedFeatureError):
        client.completion_as([UserMessage(content="Make a person")], _Person)
