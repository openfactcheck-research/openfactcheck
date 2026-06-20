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

from typing import TYPE_CHECKING, Self, cast

from pydantic import BaseModel, TypeAdapter, ValidationError

from openfactcheck.chat.backends import default_backend
from openfactcheck.chat.config import RuntimeConfig
from openfactcheck.chat.errors import StructuredOutputError, UnsupportedFeatureError
from openfactcheck.chat.partial import partial_model
from openfactcheck.chat.providers import get_provider
from openfactcheck.chat.requests import ChatRequest, ResponseFormat
from openfactcheck.chat.responses import TextDelta
from openfactcheck.messages import UserMessage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator

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

    The client keeps one pooled connection open across calls. Close it with
    [`close`][ChatClient.close] (or a `with` block) for sync use, and
    [`aclose`][ChatClient.aclose] (or an `async with` block) for async use, to
    release the pool when done.

    Note:
        Use one client within a single event loop. Sharing a client across
        separate `asyncio.run` calls reuses a pool bound to a loop that has
        since closed; run the work under one loop instead.
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

    def _format_for(self, response_model: type[BaseModel] | None) -> ResponseFormat | None:
        """Build the structured-output format for ``response_model``, or ``None`` for free text.

        Requires provider support when a model is given, so the constraint surfaces
        the same way as for [`acompletion_as`][ChatClient.acompletion_as].
        """
        if response_model is None:
            return None
        self._require_structured_output()
        return ResponseFormat(name=response_model.__name__, json_schema=response_model.model_json_schema())

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

    def stream(
        self, messages: list[Message], *, response_model: type[BaseModel] | None = None
    ) -> Iterator[StreamEvent]:
        """Stream a response as typed events.

        Args:
            messages: The conversation to send.
            response_model: When given, the reply is constrained to this model's
                JSON schema and the streamed text is that JSON, chunk by chunk.
                Omit it for free text. See [`stream_as`][ChatClient.stream_as] to
                receive parsed objects instead of raw JSON.

        Yields:
            A [`TextDelta`][TextDelta] for each content chunk, then a final
            [`StreamEnd`][StreamEnd] carrying ``finish_reason`` and ``usage``.

        Raises:
            UnsupportedFeatureError: ``response_model`` is given but the provider
                does not support structured output.
        """
        yield from self._backend.stream(self._build_request(messages, self._format_for(response_model)))

    async def astream(
        self, messages: list[Message], *, response_model: type[BaseModel] | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Stream a response as typed events over an async iterator.

        Args:
            messages: The conversation to send.
            response_model: When given, the reply is constrained to this model's
                JSON schema and the streamed text is that JSON, chunk by chunk.
                Omit it for free text. See [`astream_as`][ChatClient.astream_as] to
                receive parsed objects instead of raw JSON.

        Yields:
            A [`TextDelta`][TextDelta] for each content chunk, then a final
            [`StreamEnd`][StreamEnd] carrying ``finish_reason`` and ``usage``.

        Raises:
            UnsupportedFeatureError: ``response_model`` is given but the provider
                does not support structured output.
        """
        async for event in self._backend.astream(self._build_request(messages, self._format_for(response_model))):
            yield event

    def stream_collect(
        self,
        messages: list[Message],
        *,
        response_model: type[BaseModel] | None = None,
        on_delta: Callable[[TextDelta], None] | None = None,
    ) -> str:
        """Stream a response, observe each chunk, and return the assembled text.

        A convenience over [`stream`][ChatClient.stream] for callers that want both
        the streaming side effect (a live display, a progress sink) and the final
        text in one call, instead of collecting chunks by hand.

        Args:
            messages: The conversation to send.
            response_model: When given, constrains the reply to this model's JSON
                schema; the assembled text (and each chunk) is then that JSON.
            on_delta: Called with each [`TextDelta`][TextDelta] as it arrives, for
                example to forward tokens to a progress sink. The terminal
                [`StreamEnd`][StreamEnd] is not passed.

        Returns:
            The concatenated text of every chunk (the JSON when ``response_model``
            is given).

        Raises:
            UnsupportedFeatureError: ``response_model`` is given but the provider
                does not support structured output.
        """
        parts: list[str] = []
        for event in self.stream(messages, response_model=response_model):
            if isinstance(event, TextDelta):
                parts.append(event.content)
                if on_delta is not None:
                    on_delta(event)
        return "".join(parts)

    async def astream_collect(
        self,
        messages: list[Message],
        *,
        response_model: type[BaseModel] | None = None,
        on_delta: Callable[[TextDelta], None] | None = None,
    ) -> str:
        """Stream a response over an async iterator, observe each chunk, and return the assembled text.

        Async peer of [`stream_collect`][ChatClient.stream_collect]; same behavior.

        Args:
            messages: The conversation to send.
            response_model: When given, constrains the reply to this model's JSON
                schema; the assembled text (and each chunk) is then that JSON.
            on_delta: Called with each [`TextDelta`][TextDelta] as it arrives, for
                example to forward tokens to a progress sink. The terminal
                [`StreamEnd`][StreamEnd] is not passed.

        Returns:
            The concatenated text of every chunk (the JSON when ``response_model``
            is given).

        Raises:
            UnsupportedFeatureError: ``response_model`` is given but the provider
                does not support structured output.
        """
        parts: list[str] = []
        async for event in self.astream(messages, response_model=response_model):
            if isinstance(event, TextDelta):
                parts.append(event.content)
                if on_delta is not None:
                    on_delta(event)
        return "".join(parts)

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

    def stream_as[T: BaseModel](self, messages: list[Message], response_model: type[T]) -> Iterator[T]:
        """Stream a structured reply as progressively complete instances.

        Asks the model to reply with JSON matching ``response_model`` and yields
        the object as it is built: each item carries the fields that have arrived
        so far, the rest left unset, and the final item is the complete, validated
        instance. Useful for showing a field (a verdict's reasoning, an answer)
        filling in live while still ending with a fully typed result.

        Unlike [`completion_as`][ChatClient.completion_as], a failed final
        validation is not retried; streaming cannot replay a partial reply.

        Args:
            messages: The conversation to send.
            response_model: The Pydantic model the reply must conform to.

        Yields:
            Progressively complete instances of ``response_model``; the final one
            is fully validated.

        Raises:
            UnsupportedFeatureError: The provider does not support structured
                output.
            StructuredOutputError: The complete reply failed validation.
        """
        self._require_structured_output()
        response_format = ResponseFormat(
            name=response_model.__name__,
            json_schema=response_model.model_json_schema(),
        )
        adapter = TypeAdapter(partial_model(response_model))
        raw = ""
        for event in self._backend.stream(self._build_request(messages, response_format)):
            if not isinstance(event, TextDelta):
                continue
            raw += event.content
            try:
                partial = adapter.validate_json(raw, experimental_allow_partial="trailing-strings")
            except ValidationError:
                continue
            yield cast("T", partial)
        try:
            yield response_model.model_validate_json(raw)
        except ValidationError as exc:
            raise StructuredOutputError(
                f"reply did not match {response_model.__name__}.",
                raw=raw,
                validation_error=exc,
            ) from exc

    async def astream_as[T: BaseModel](self, messages: list[Message], response_model: type[T]) -> AsyncIterator[T]:
        """Stream a structured reply over an async iterator as progressively complete instances.

        Async peer of [`stream_as`][ChatClient.stream_as]; same progressive
        behavior and same no-retry contract.

        Args:
            messages: The conversation to send.
            response_model: The Pydantic model the reply must conform to.

        Yields:
            Progressively complete instances of ``response_model``; the final one
            is fully validated.

        Raises:
            UnsupportedFeatureError: The provider does not support structured
                output.
            StructuredOutputError: The complete reply failed validation.
        """
        self._require_structured_output()
        response_format = ResponseFormat(
            name=response_model.__name__,
            json_schema=response_model.model_json_schema(),
        )
        adapter = TypeAdapter(partial_model(response_model))
        raw = ""
        async for event in self._backend.astream(self._build_request(messages, response_format)):
            if not isinstance(event, TextDelta):
                continue
            raw += event.content
            try:
                partial = adapter.validate_json(raw, experimental_allow_partial="trailing-strings")
            except ValidationError:
                continue
            yield cast("T", partial)
        try:
            yield response_model.model_validate_json(raw)
        except ValidationError as exc:
            raise StructuredOutputError(
                f"reply did not match {response_model.__name__}.",
                raw=raw,
                validation_error=exc,
            ) from exc

    def close(self) -> None:
        """Release the pooled sync connection.

        Pairs with the sync call methods; safe to call more than once. Prefer a
        `with` block, which calls this on exit.
        """
        self._backend.close()

    async def aclose(self) -> None:
        """Release the pooled async connection.

        Pairs with the async call methods; safe to call more than once. Prefer an
        `async with` block, which calls this on exit.
        """
        await self._backend.aclose()

    def __enter__(self) -> Self:
        """Enter a sync context that closes the client on exit."""
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Close the client on leaving a `with` block."""
        self.close()

    async def __aenter__(self) -> Self:
        """Enter an async context that closes the client on exit."""
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Close the client on leaving an `async with` block."""
        await self.aclose()
