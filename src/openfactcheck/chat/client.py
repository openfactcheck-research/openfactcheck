"""Stateful facade for the chat layer.

[`ChatClient`][ChatClient] is the one type most callers touch. Construct it
once with a [`ModelConfig`][ModelConfig], then use its four methods to send a
list of [`Message`][Message] values and receive either a single
[`ChatResponse`][ChatResponse] or a stream of [`StreamEvent`][StreamEvent]
values.

Every method comes in sync and async variants:

- [`ChatClient.completion`][ChatClient.completion] and
  [`ChatClient.acompletion`][ChatClient.acompletion] for single-shot calls.
- [`ChatClient.stream`][ChatClient.stream] and
  [`ChatClient.astream`][ChatClient.astream] for streaming.

All four raise [`ChatModelError`][ChatModelError] subclasses on failure.

Example:
    ```python
    from openfactcheck.chat import ChatClient, OpenAIConfig, UserMessage

    client = ChatClient(config=OpenAIConfig(model="gpt-4o"))
    response = client.completion([UserMessage(content="Hello")])
    print(response.message.content)
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.backends import _default_backend  # pyright: ignore[reportPrivateUsage] - internal API.
from openfactcheck.chat.config import RuntimeConfig
from openfactcheck.chat.providers import get_provider
from openfactcheck.chat.requests import ChatRequest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from openfactcheck.chat.backends.base import ChatBackend
    from openfactcheck.chat.config import ModelConfig
    from openfactcheck.chat.messages import Message
    from openfactcheck.chat.responses import ChatResponse, StreamEvent


class ChatClient:
    """Configured chat client. Create once, call many times.

    Offers sync and async variants of both single-shot
    ([`completion`][ChatClient.completion] /
    [`acompletion`][ChatClient.acompletion]) and streaming
    ([`stream`][ChatClient.stream] /
    [`astream`][ChatClient.astream]) calls.

    All four methods raise [`ChatModelError`][ChatModelError] subclasses on
    failure, most commonly
    [`AuthenticationError`][AuthenticationError],
    [`RateLimitError`][RateLimitError],
    [`ProviderError`][ProviderError], or
    [`UnsupportedFeatureError`][UnsupportedFeatureError].
    """

    def __init__(
        self,
        config: ModelConfig,
        runtime: RuntimeConfig | None = None,
        backend: ChatBackend | None = None,
    ) -> None:
        """Build and validate a chat client.

        Args:
            config: Model-specific configuration. Validated eagerly against
                the matching [`BaseProvider`][BaseProvider], so configuration
                errors surface here instead of on the first call.
            runtime: Execution-level settings such as timeout and retries.
                Defaults to an empty [`RuntimeConfig`][RuntimeConfig].
            backend: Backend implementation. Defaults to the direct-SDK
                backend for the configured provider (for example
                [`OpenAIBackend`][OpenAIBackend]). Pass an explicit backend
                only to override that default.

        Raises:
            ProviderNotFoundError: Provider name is not registered or its
                SDK is not installed.
            ProviderError: Configuration is rejected by the provider.
        """
        self._config = config
        self._runtime = runtime if runtime is not None else RuntimeConfig()
        self._provider = get_provider(config.provider)
        self._provider.validate_config(config)
        self._backend: ChatBackend = backend if backend is not None else _default_backend(config.provider)

    def _build_request(self, messages: list[Message]) -> ChatRequest:
        return ChatRequest(messages=messages, config=self._config, runtime=self._runtime)

    def completion(self, messages: list[Message]) -> ChatResponse:
        """Send messages and return a complete response.

        Args:
            messages: The conversation to send.

        Returns:
            The model's reply along with token usage and finish reason.
        """
        return self._backend.completion(self._build_request(messages))

    async def acompletion(self, messages: list[Message]) -> ChatResponse:
        """Send messages and await a complete response.

        Args:
            messages: The conversation to send.

        Returns:
            The model's reply along with token usage and finish reason.
        """
        return await self._backend.acompletion(self._build_request(messages))

    def stream(self, messages: list[Message]) -> Iterator[StreamEvent]:
        """Stream a response as typed events.

        Args:
            messages: The conversation to send.

        Yields:
            A [`TextDelta`][TextDelta] for each content chunk, then a final
            [`StreamEnd`][StreamEnd] carrying ``finish_reason`` and ``usage``.
        """
        yield from self._backend.stream(self._build_request(messages))

    async def astream(self, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        """Stream a response as typed events over an async iterator.

        Args:
            messages: The conversation to send.

        Yields:
            A [`TextDelta`][TextDelta] for each content chunk, then a final
            [`StreamEnd`][StreamEnd] carrying ``finish_reason`` and ``usage``.
        """
        async for event in self._backend.astream(self._build_request(messages)):
            yield event
