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
    from openfactcheck.chat import ChatClient, OpenAIConfig
    from openfactcheck.messages import UserMessage

    client = ChatClient(config=OpenAIConfig(model="gpt-4o"))
    response = client.completion([UserMessage(content="Hello")])
    print(response.message.content)
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ValidationError

from openfactcheck.chat.backends import default_backend
from openfactcheck.chat.config import RuntimeConfig
from openfactcheck.chat.errors import StructuredOutputError, UnsupportedFeatureError
from openfactcheck.chat.providers import get_provider
from openfactcheck.chat.requests import ChatRequest, ResponseFormat
from openfactcheck.messages import UserMessage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from openfactcheck.chat.backends.base import ChatBackend
    from openfactcheck.chat.config import ModelConfig
    from openfactcheck.chat.responses import ChatResponse, StreamEvent
    from openfactcheck.messages import Message


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
        self._backend: ChatBackend = backend if backend is not None else default_backend(config.provider)

    def _build_request(self, messages: list[Message], response_format: ResponseFormat | None = None) -> ChatRequest:
        return ChatRequest(
            messages=messages,
            config=self._config,
            runtime=self._runtime,
            response_format=response_format,
        )

    def _require_structured_output(self) -> None:
        """Raise if the configured provider does not support structured output."""
        if not self._provider.capabilities.structured_output:
            raise UnsupportedFeatureError(f"provider '{self._config.provider}' does not support structured output.")

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

    def completion_as[T: BaseModel](self, messages: list[Message], response_model: type[T]) -> T:
        """Send messages and return a validated instance of ``response_model``.

        Asks the model to reply with JSON matching ``response_model`` and
        validates the reply into an instance. On a validation failure, the
        error is sent back to the model and the call retried up to
        [`max_parse_retries`][RuntimeConfig.max_parse_retries] times before
        raising.

        Args:
            messages: The conversation to send.
            response_model: The Pydantic model the reply must conform to.

        Returns:
            A validated instance of ``response_model``.

        Raises:
            UnsupportedFeatureError: The provider does not support structured
                output.
            StructuredOutputError: The reply still failed validation after the
                allowed retries.
        """
        self._require_structured_output()
        response_format = ResponseFormat(
            name=response_model.__name__,
            json_schema=response_model.model_json_schema(),
        )
        conversation = list(messages)
        retries_left = self._runtime.max_parse_retries
        while True:
            response = self._backend.completion(self._build_request(conversation, response_format))
            raw = response.message.content
            try:
                return response_model.model_validate_json(raw)
            except ValidationError as exc:
                if retries_left <= 0:
                    raise StructuredOutputError(
                        f"reply did not match {response_model.__name__} after retries.",
                        raw=raw,
                        validation_error=exc,
                    ) from exc
                retries_left -= 1
                reprompt = UserMessage(
                    content=(
                        "Your previous reply did not match the required schema. "
                        f"Fix these errors and return only valid JSON:\n{exc}"
                    ),
                )
                conversation = [*conversation, response.message, reprompt]

    async def acompletion_as[T: BaseModel](self, messages: list[Message], response_model: type[T]) -> T:
        """Send messages and await a validated instance of ``response_model``.

        Async peer of [`completion_as`][ChatClient.completion_as]; same
        validation and retry behavior.

        Args:
            messages: The conversation to send.
            response_model: The Pydantic model the reply must conform to.

        Returns:
            A validated instance of ``response_model``.

        Raises:
            UnsupportedFeatureError: The provider does not support structured
                output.
            StructuredOutputError: The reply still failed validation after the
                allowed retries.
        """
        self._require_structured_output()
        response_format = ResponseFormat(
            name=response_model.__name__,
            json_schema=response_model.model_json_schema(),
        )
        conversation = list(messages)
        retries_left = self._runtime.max_parse_retries
        while True:
            response = await self._backend.acompletion(self._build_request(conversation, response_format))
            raw = response.message.content
            try:
                return response_model.model_validate_json(raw)
            except ValidationError as exc:
                if retries_left <= 0:
                    raise StructuredOutputError(
                        f"reply did not match {response_model.__name__} after retries.",
                        raw=raw,
                        validation_error=exc,
                    ) from exc
                retries_left -= 1
                reprompt = UserMessage(
                    content=(
                        "Your previous reply did not match the required schema. "
                        f"Fix these errors and return only valid JSON:\n{exc}"
                    ),
                )
                conversation = [*conversation, response.message, reprompt]
