"""Protocol for chat execution backends.

A backend owns the actual SDK call for a given provider.
[`ChatBackend`][ChatBackend] is the replaceable execution boundary that
[`ChatClient`][ChatClient] talks to; the rest of the chat layer depends
only on the protocol, never on a concrete backend.

Four methods describe the full surface: sync and async variants of
single-shot completion and streaming. Implementations accept a
[`ChatRequest`][ChatRequest] and produce a [`ChatResponse`][ChatResponse]
or a stream of [`StreamEvent`][StreamEvent] values, mapping any SDK or
transport error to a [`ChatModelError`][ChatModelError] subclass.

See [`OpenAIBackend`][OpenAIBackend] for a reference implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from openfactcheck.chat.requests import ChatRequest
    from openfactcheck.chat.responses import ChatResponse, StreamEvent


class ChatBackend(Protocol):
    """Execution backend for a single chat provider.

    Implementations take a [`ChatRequest`][ChatRequest], issue the provider
    SDK call, and return a [`ChatResponse`][ChatResponse] or a stream of
    [`StreamEvent`][StreamEvent] values. Errors are mapped to
    [`ChatModelError`][ChatModelError] subclasses so callers handle a
    single error surface regardless of the underlying SDK.
    """

    def completion(self, request: ChatRequest) -> ChatResponse:
        """Execute a single chat completion and return the full response.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Returns:
            The model's reply along with token usage and finish reason.

        Raises:
            ChatModelError: On any failure (authentication, rate limit,
                provider error, unsupported feature, etc.).
        """
        ...

    async def acompletion(self, request: ChatRequest) -> ChatResponse:
        """Execute a single chat completion asynchronously and return the full response.

        Args:
            request: Messages, model configuration, and runtime settings
                bundled for the call.

        Returns:
            The model's reply along with token usage and finish reason.

        Raises:
            ChatModelError: On any failure.
        """
        ...

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
            ChatModelError: On any failure.
        """
        ...

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
            ChatModelError: On any failure.
        """
        ...
