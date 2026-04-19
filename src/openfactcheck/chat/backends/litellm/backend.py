"""Chat backend that routes through litellm.

Implements the [`ChatBackend`][ChatBackend] protocol by dispatching every
provider through litellm's single ``completion`` / ``acompletion`` entry
point. Use this backend when you want one multi-provider gateway, a unified
pricing layer, or litellm's routing features on top of OpenFactCheck's
configs and messages.

Users opt in by passing an explicit instance to
[`ChatClient`][ChatClient]; the default backend picker in
``openfactcheck.chat.backends`` returns a direct-SDK backend instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.backends.litellm.imports import load_litellm
from openfactcheck.chat.backends.litellm.normalize import (
    OpenAIMessage,
    map_error,
    to_chat_response,
    to_openai_messages,
    to_stream_end,
)
from openfactcheck.chat.backends.litellm.params import Kwargs, config_to_kwargs
from openfactcheck.chat.responses import TextDelta

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from types import ModuleType

    from litellm.types.utils import ModelResponseStream

    from openfactcheck.chat.requests import ChatRequest
    from openfactcheck.chat.responses import ChatResponse, StreamEvent

_STREAM_KWARGS: Kwargs = {"stream": True, "stream_options": {"include_usage": True}}


class LiteLLMBackend:
    """Chat backend that routes through litellm.

    Satisfies the [`ChatBackend`][ChatBackend] protocol. Supports every
    provider litellm recognizes, so the same backend instance can service
    any [`ModelConfig`][ModelConfig] the application dispatches.
    """

    def _prepare(
        self,
        request: ChatRequest,
        *,
        stream: bool = False,
    ) -> tuple[ModuleType, Kwargs, list[OpenAIMessage]]:
        """Load litellm, build kwargs, and convert messages for ``request``."""
        litellm = load_litellm()
        kwargs = config_to_kwargs(request.config, request.runtime)
        if stream:
            kwargs.update(_STREAM_KWARGS)
        messages = to_openai_messages(request.messages)
        return litellm, kwargs, messages

    def completion(self, request: ChatRequest) -> ChatResponse:
        """Execute a single chat completion and return the full response.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Returns:
            The model's reply along with token usage and finish reason.

        Raises:
            ChatModelError: On any litellm or transport failure.
        """
        litellm, kwargs, messages = self._prepare(request)
        try:
            response = litellm.completion(messages=messages, **kwargs)
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
            ChatModelError: On any litellm or transport failure.
        """
        litellm, kwargs, messages = self._prepare(request)
        try:
            response = await litellm.acompletion(messages=messages, **kwargs)
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
            ChatModelError: On any litellm or transport failure.
        """
        litellm, kwargs, messages = self._prepare(request, stream=True)
        try:
            stream_iter = litellm.completion(messages=messages, **kwargs)
        except Exception as exc:
            raise map_error(exc) from exc

        last_chunk: ModelResponseStream | None = None
        accumulated_usage: object = None
        try:
            for chunk in stream_iter:
                last_chunk = chunk
                if getattr(chunk, "usage", None):
                    accumulated_usage = chunk.usage
                if chunk.choices:
                    content = getattr(chunk.choices[0].delta, "content", None)
                    if content:
                        yield TextDelta(content=content)
        except Exception as exc:
            raise map_error(exc) from exc

        yield to_stream_end(last_chunk, accumulated_usage)

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
            ChatModelError: On any litellm or transport failure.
        """
        litellm, kwargs, messages = self._prepare(request, stream=True)
        try:
            stream_iter = await litellm.acompletion(messages=messages, **kwargs)
        except Exception as exc:
            raise map_error(exc) from exc

        last_chunk: ModelResponseStream | None = None
        accumulated_usage: object = None
        try:
            async for chunk in stream_iter:
                last_chunk = chunk
                if getattr(chunk, "usage", None):
                    accumulated_usage = chunk.usage
                if chunk.choices:
                    content = getattr(chunk.choices[0].delta, "content", None)
                    if content:
                        yield TextDelta(content=content)
        except Exception as exc:
            raise map_error(exc) from exc

        yield to_stream_end(last_chunk, accumulated_usage)
