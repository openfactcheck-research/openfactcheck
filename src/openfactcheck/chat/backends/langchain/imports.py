"""Lazy import dispatch for LangChain provider classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.errors import ProviderNotFoundError

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


_INSTALL_HINT = "Install with: pip install openfactcheck[langchain]"


def get_langchain_class(provider: str) -> type[BaseChatModel]:
    """Lazily import the langchain chat model class for *provider*."""
    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ProviderNotFoundError(f"Provider '{provider}' requires langchain-openai. {_INSTALL_HINT}") from None
        return ChatOpenAI
    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ProviderNotFoundError(
                f"Provider '{provider}' requires langchain-anthropic. {_INSTALL_HINT}"
            ) from None
        return ChatAnthropic
    raise ProviderNotFoundError(f"LangChain backend does not support provider '{provider}'.")
