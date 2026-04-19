"""Lazy import of the ``openai`` SDK clients."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.errors import ProviderNotFoundError

if TYPE_CHECKING:
    from openai import AsyncOpenAI, OpenAI


def load_openai() -> type[OpenAI]:
    """Lazily import and return the ``OpenAI`` sync client class."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ProviderNotFoundError(
            "OpenAI backend requires the openai SDK. Install with: pip install openfactcheck[openai]"
        ) from None
    return OpenAI


def load_async_openai() -> type[AsyncOpenAI]:
    """Lazily import and return the ``AsyncOpenAI`` async client class."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise ProviderNotFoundError(
            "OpenAI backend requires the openai SDK. Install with: pip install openfactcheck[openai]"
        ) from None
    return AsyncOpenAI
