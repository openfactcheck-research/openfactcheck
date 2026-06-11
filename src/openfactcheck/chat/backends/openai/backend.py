"""Direct-SDK chat backend for OpenAI.

Implements the [`ChatBackend`][ChatBackend] protocol by calling the
``openai`` SDK directly, with no gateway or wrapper library in between.
All ``openai`` imports are isolated to this subpackage so replacing or
removing the SDK only changes files under
``openfactcheck.chat.backends.openai``.

Users rarely construct [`OpenAIBackend`][OpenAIBackend] explicitly;
[`ChatClient`][ChatClient] uses it automatically when
``config.provider`` is ``"openai"``. Pass it by hand only when combining
it with other non-default [`ChatClient`][ChatClient] settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.backends.openai.imports import load_async_openai, load_openai
from openfactcheck.chat.backends.openai.normalize import (
    OpenAIMessage,
    map_error,
    to_chat_response,
    to_openai_messages,
    to_stream_end,
)
from openfactcheck.chat.backends.openai.params import Kwargs, config_to_kwargs, response_format_kwargs
from openfactcheck.chat.responses import TextDelta

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from openai import AsyncOpenAI, OpenAI
    from openai.types.chat import ChatCompletionChunk

    from openfactcheck.chat.requests import ChatRequest
    from openfactcheck.chat.responses import ChatResponse, StreamEvent


class OpenAIBackend:
    """Direct-SDK chat backend for OpenAI.

    Satisfies the [`ChatBackend`][ChatBackend] protocol. Accepts
    OpenAI-compatible provider configs; passing any other provider's config
    raises [`UnsupportedFeatureError`][UnsupportedFeatureError]. The base URL
    and API key are configurable so the same SDK can target any
    OpenAI-compatible endpoint.
    """

    def __init__(self, *, base_url: str | None = None, api_key: str | None = None) -> None:
        """Build the backend, optionally targeting an OpenAI-compatible endpoint.

        Args:
            base_url: API base URL to call. Unset uses the standard OpenAI
                endpoint; set it to target a compatible endpoint such as
                OpenRouter.
            api_key: API key to authenticate with. Unset reads the standard
                ``OPENAI_API_KEY`` environment variable.
        """
        self._base_url = base_url
        self._api_key = api_key

    def _client(self, request: ChatRequest) -> OpenAI:
        """Build a sync SDK client for ``request``."""
        return load_openai()(
            timeout=request.runtime.timeout,
            max_retries=request.runtime.max_retries,
            base_url=self._base_url,
            api_key=self._api_key,
        )

    def _aclient(self, request: ChatRequest) -> AsyncOpenAI:
        """Build an async SDK client for ``request``."""
        return load_async_openai()(
            timeout=request.runtime.timeout,
            max_retries=request.runtime.max_retries,
            base_url=self._base_url,
            api_key=self._api_key,
        )

    def _prepare(self, request: ChatRequest) -> tuple[Kwargs, list[OpenAIMessage]]:
        """Build SDK kwargs and convert messages for ``request``."""
        kwargs = config_to_kwargs(request.config)
        if request.response_format is not None:
            kwargs.update(response_format_kwargs(request.response_format))
        messages = to_openai_messages(request.messages)
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
            response = client.chat.completions.create(messages=messages, **kwargs)
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
            response = await client.chat.completions.create(messages=messages, **kwargs)
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
            stream_iter = client.chat.completions.create(
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                **kwargs,
            )
        except Exception as exc:
            raise map_error(exc) from exc

        last_chunk: ChatCompletionChunk | None = None
        accumulated_usage: object = None
        try:
            for chunk in stream_iter:
                last_chunk = chunk
                if chunk.usage is not None:
                    accumulated_usage = chunk.usage
                if chunk.choices:
                    content = chunk.choices[0].delta.content
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
            ChatModelError: On any SDK or transport failure.
        """
        kwargs, messages = self._prepare(request)
        client = self._aclient(request)
        try:
            stream_iter = await client.chat.completions.create(
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                **kwargs,
            )
        except Exception as exc:
            raise map_error(exc) from exc

        last_chunk: ChatCompletionChunk | None = None
        accumulated_usage: object = None
        try:
            async for chunk in stream_iter:
                last_chunk = chunk
                if chunk.usage is not None:
                    accumulated_usage = chunk.usage
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield TextDelta(content=content)
        except Exception as exc:
            raise map_error(exc) from exc

        yield to_stream_end(last_chunk, accumulated_usage)
