"""Chat backend that routes through LangChain.

Implements the [`ChatBackend`][ChatBackend] protocol by dispatching to the
matching ``langchain_<provider>`` integration package (for example
``langchain_openai``). Use this backend when you want to reuse LangChain
tooling, agents, or callbacks with OpenFactCheck's configs and messages.

Users opt in by passing an explicit instance to
[`ChatClient`][ChatClient]; the default backend picker in
``openfactcheck.chat.backends`` returns a direct-SDK backend instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.backends.langchain.imports import get_langchain_class
from openfactcheck.chat.backends.langchain.normalize import (
    to_chat_response,
    to_langchain_messages,
    to_stream_end,
)
from openfactcheck.chat.backends.langchain.params import config_to_kwargs
from openfactcheck.chat.responses import TextDelta

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessageChunk, BaseMessage

    from openfactcheck.chat.requests import ChatRequest
    from openfactcheck.chat.responses import ChatResponse, StreamEvent


class LangChainBackend:
    """Chat backend that routes through LangChain.

    Satisfies the [`ChatBackend`][ChatBackend] protocol. Supports every
    provider for which a ``langchain_<provider>`` integration package is
    installed, so the same backend instance can service any
    [`ModelConfig`][ModelConfig] the application dispatches.
    """

    def _prepare(self, request: ChatRequest) -> tuple[BaseChatModel, list[BaseMessage]]:
        """Build the LangChain model and messages for ``request``."""
        cls = get_langchain_class(request.config.provider)
        kwargs = config_to_kwargs(request.config, request.runtime)
        model = cls(**kwargs)
        lc_messages = to_langchain_messages(request.messages)
        return model, lc_messages

    def completion(self, request: ChatRequest) -> ChatResponse:
        """Execute a single chat completion and return the full response.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Returns:
            The model's reply along with token usage and finish reason.

        Raises:
            ChatModelError: On any LangChain or transport failure.
        """
        model, lc_messages = self._prepare(request)
        result = model.invoke(lc_messages)
        return to_chat_response(result, request.config.model, request.config.provider)

    async def acompletion(self, request: ChatRequest) -> ChatResponse:
        """Execute a single chat completion asynchronously and return the full response.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Returns:
            The model's reply along with token usage and finish reason.

        Raises:
            ChatModelError: On any LangChain or transport failure.
        """
        model, lc_messages = self._prepare(request)
        result = await model.ainvoke(lc_messages)
        return to_chat_response(result, request.config.model, request.config.provider)

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
            ChatModelError: On any LangChain or transport failure.
        """
        model, lc_messages = self._prepare(request)

        accumulated: AIMessageChunk | None = None
        for chunk in model.stream(lc_messages):
            accumulated = chunk if accumulated is None else accumulated + chunk
            content = chunk.content if isinstance(chunk.content, str) else ""
            if content:
                yield TextDelta(content=content)

        yield to_stream_end(accumulated)

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
            ChatModelError: On any LangChain or transport failure.
        """
        model, lc_messages = self._prepare(request)

        accumulated: AIMessageChunk | None = None
        async for chunk in model.astream(lc_messages):
            accumulated = chunk if accumulated is None else accumulated + chunk
            content = chunk.content if isinstance(chunk.content, str) else ""
            if content:
                yield TextDelta(content=content)

        yield to_stream_end(accumulated)
