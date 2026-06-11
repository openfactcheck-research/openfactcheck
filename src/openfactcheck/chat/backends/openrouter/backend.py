"""Chat backend for OpenRouter.

OpenRouter exposes an OpenAI-compatible Chat Completions API, so this
backend serves it by reusing [`OpenAIBackend`][OpenAIBackend] pointed at
OpenRouter's endpoint with an OpenRouter API key. No new SDK import lives
here: the ``openai`` SDK stays isolated to
``openfactcheck.chat.backends.openai``.

Users rarely construct [`OpenRouterBackend`][OpenRouterBackend] explicitly;
[`ChatClient`][ChatClient] uses it automatically when ``config.provider``
is ``"openrouter"``.
"""

import os

from openfactcheck.chat.backends.openai.backend import OpenAIBackend
from openfactcheck.chat.errors import AuthenticationError

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
"""Base URL of OpenRouter's OpenAI-compatible Chat Completions API."""


class OpenRouterBackend(OpenAIBackend):
    """Chat backend for OpenRouter.

    Serves OpenRouter's OpenAI-compatible Chat Completions API by reusing
    [`OpenAIBackend`][OpenAIBackend] with OpenRouter's base URL and API key.
    Accepts [`OpenRouterConfig`][OpenRouterConfig].
    """

    def __init__(self, *, api_key: str | None = None, base_url: str = OPENROUTER_BASE_URL) -> None:
        """Build an OpenRouter backend.

        Args:
            api_key: OpenRouter API key. Unset reads the ``OPENROUTER_API_KEY``
                environment variable.
            base_url: OpenRouter API base URL.

        Raises:
            AuthenticationError: If no key is passed and ``OPENROUTER_API_KEY``
                is unset.
        """
        key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise AuthenticationError("OpenRouter requires an API key; set OPENROUTER_API_KEY or pass api_key.")
        super().__init__(base_url=base_url, api_key=key)
