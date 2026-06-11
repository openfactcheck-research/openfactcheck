"""OpenRouter chat backend package.

OpenRouter speaks OpenAI's Chat Completions protocol, so this backend
reuses the ``openai`` SDK backend rather than importing a new SDK. The
``openai`` SDK stays isolated to ``openfactcheck.chat.backends.openai``.
"""

from openfactcheck.chat.backends.openrouter.backend import OpenRouterBackend

__all__ = ["OpenRouterBackend"]
