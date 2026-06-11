"""Direct-SDK chat backend for Anthropic.

Implements the [`ChatBackend`][ChatBackend] protocol by calling the
``anthropic`` SDK directly, with no gateway or wrapper library in between.
All ``anthropic`` imports are isolated to this subpackage so replacing or
removing the SDK only changes files under
``openfactcheck.chat.backends.anthropic``.

Users rarely construct [`AnthropicBackend`][AnthropicBackend] explicitly;
[`ChatClient`][ChatClient] uses it automatically when
``config.provider`` is ``"anthropic"``. Pass it by hand only when combining
it with other non-default [`ChatClient`][ChatClient] settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.backends.anthropic.imports import load_anthropic, load_async_anthropic
from openfactcheck.chat.backends.anthropic.normalize import (
    AnthropicInputMessage,
    map_error,
    to_anthropic_messages,
    to_chat_response,
    to_stream_end,
)
from openfactcheck.chat.backends.anthropic.params import Kwargs, config_to_kwargs
from openfactcheck.chat.responses import TextDelta

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from anthropic import Anthropic, AsyncAnthropic

    from openfactcheck.chat.requests import ChatRequest
    from openfactcheck.chat.responses import ChatResponse, StreamEvent


class AnthropicBackend:
    """Direct-SDK chat backend for Anthropic.

    Satisfies the [`ChatBackend`][ChatBackend] protocol. Accepts
    [`AnthropicConfig`][AnthropicConfig] only; passing a config from
    another provider raises
    [`UnsupportedFeatureError`][UnsupportedFeatureError]. Anthropic's API
    rejects requests without an explicit output cap, so ``max_output_tokens``
    must be set on the config.
    """

    def _client(self, request: ChatRequest) -> Anthropic:
        """Build a sync SDK client for ``request``."""
        return load_anthropic()(timeout=request.runtime.timeout, max_retries=request.runtime.max_retries)

    def _aclient(self, request: ChatRequest) -> AsyncAnthropic:
        """Build an async SDK client for ``request``."""
        return load_async_anthropic()(timeout=request.runtime.timeout, max_retries=request.runtime.max_retries)

    def _prepare(self, request: ChatRequest) -> tuple[Kwargs, list[AnthropicInputMessage]]:
        """Build SDK kwargs and convert messages. System prompt is merged into kwargs."""
        kwargs = config_to_kwargs(request.config)
        system, messages = to_anthropic_messages(request.messages)
        if system is not None:
            kwargs["system"] = system
        return kwargs, messages

    def completion(self, request: ChatRequest) -> ChatResponse:
        """Execute a single chat completion and return the full response.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Returns:
            The model's reply along with token usage and finish reason.

        Raises:
            ChatModelError: On any SDK or transport failure.
        """
        kwargs, messages = self._prepare(request)
        client = self._client(request)
        try:
            response = client.messages.create(messages=messages, **kwargs)
        except Exception as exc:
            raise map_error(exc) from exc
        return to_chat_response(response, request.config.model, request.config.provider)

    async def acompletion(self, request: ChatRequest) -> ChatResponse:
        """Execute a single chat completion asynchronously and return the full response.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Returns:
            The model's reply along with token usage and finish reason.

        Raises:
            ChatModelError: On any SDK or transport failure.
        """
        kwargs, messages = self._prepare(request)
        client = self._aclient(request)
        try:
            response = await client.messages.create(messages=messages, **kwargs)
        except Exception as exc:
            raise map_error(exc) from exc
        return to_chat_response(response, request.config.model, request.config.provider)

    def stream(self, request: ChatRequest) -> Iterator[StreamEvent]:
        """Stream a chat completion as typed events.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Yields:
            A [`TextDelta`][TextDelta] for each content chunk, then a
            final [`StreamEnd`][StreamEnd] carrying ``finish_reason`` and
            ``usage``.

        Raises:
            ChatModelError: On any SDK or transport failure.
        """
        kwargs, messages = self._prepare(request)
        client = self._client(request)
        try:
            stream_iter = client.messages.create(messages=messages, stream=True, **kwargs)
        except Exception as exc:
            raise map_error(exc) from exc

        input_tokens = 0
        output_tokens = 0
        stop_reason: str | None = None
        try:
            for event in stream_iter:
                if event.type == "message_start":
                    input_tokens = event.message.usage.input_tokens
                elif event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield TextDelta(content=event.delta.text)
                elif event.type == "message_delta":
                    output_tokens = event.usage.output_tokens
                    if event.delta.stop_reason is not None:
                        stop_reason = event.delta.stop_reason
        except Exception as exc:
            raise map_error(exc) from exc

        yield to_stream_end(stop_reason, input_tokens, output_tokens)

    async def astream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """Stream a chat completion as typed events over an async iterator.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Yields:
            A [`TextDelta`][TextDelta] for each content chunk, then a
            final [`StreamEnd`][StreamEnd] carrying ``finish_reason`` and
            ``usage``.

        Raises:
            ChatModelError: On any SDK or transport failure.
        """
        kwargs, messages = self._prepare(request)
        client = self._aclient(request)
        try:
            stream_iter = await client.messages.create(messages=messages, stream=True, **kwargs)
        except Exception as exc:
            raise map_error(exc) from exc

        input_tokens = 0
        output_tokens = 0
        stop_reason: str | None = None
        try:
            async for event in stream_iter:
                if event.type == "message_start":
                    input_tokens = event.message.usage.input_tokens
                elif event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield TextDelta(content=event.delta.text)
                elif event.type == "message_delta":
                    output_tokens = event.usage.output_tokens
                    if event.delta.stop_reason is not None:
                        stop_reason = event.delta.stop_reason
        except Exception as exc:
            raise map_error(exc) from exc

        yield to_stream_end(stop_reason, input_tokens, output_tokens)
