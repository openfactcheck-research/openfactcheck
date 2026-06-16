"""Public API for the chat layer.

Build a [`ChatClient`][ChatClient] with a provider-specific configuration
(for example [`OpenAIConfig`][OpenAIConfig]), send it a list of
[`Message`][openfactcheck.messages.Message] values, and receive a [`ChatResponse`][ChatResponse] or
a stream of [`StreamEvent`][StreamEvent] values. Failures raise
[`ChatModelError`][ChatModelError] subclasses.

Import the chat API from ``openfactcheck.chat`` directly; submodule paths are
not part of the public API. Message types live in the ``openfactcheck.messages``
package.

Example:
    ```python
    from openfactcheck.chat import ChatClient, OpenAIConfig
    from openfactcheck.messages import SystemMessage, UserMessage

    client = ChatClient(config=OpenAIConfig(model="gpt-4o"))
    response = client.completion(
        [
            SystemMessage(content="You are a fact-checker."),
            UserMessage(content="Is the sky blue?"),
        ]
    )
    print(response.message.content)
    ```
"""

from openfactcheck.chat.backends.anthropic import AnthropicBackend
from openfactcheck.chat.backends.base import ChatBackend
from openfactcheck.chat.backends.openai import OpenAIBackend
from openfactcheck.chat.backends.openrouter import OpenRouterBackend
from openfactcheck.chat.client import ChatClient
from openfactcheck.chat.config import (
    AnthropicConfig,
    ModelConfig,
    OpenAIConfig,
    OpenRouterConfig,
    ProviderName,
    RuntimeConfig,
)
from openfactcheck.chat.errors import (
    AuthenticationError,
    ChatModelError,
    ProviderError,
    ProviderNotFoundError,
    RateLimitError,
    StructuredOutputError,
    UnsupportedFeatureError,
)
from openfactcheck.chat.providers.base import BaseProvider, ProviderCapabilities
from openfactcheck.chat.requests import ChatRequest, ResponseFormat
from openfactcheck.chat.responses import ChatResponse, FinishReason, StreamEnd, StreamEvent, TextDelta, Usage

# Client
__all__ = [
    "ChatClient",
]

# Configuration
__all__ += [
    "AnthropicConfig",
    "ModelConfig",
    "OpenAIConfig",
    "OpenRouterConfig",
    "ProviderName",
    "RuntimeConfig",
]

# Requests and responses
__all__ += [
    "ChatRequest",
    "ChatResponse",
    "FinishReason",
    "ResponseFormat",
    "StreamEnd",
    "StreamEvent",
    "TextDelta",
    "Usage",
]

# Errors
__all__ += [
    "AuthenticationError",
    "ChatModelError",
    "ProviderError",
    "ProviderNotFoundError",
    "RateLimitError",
    "StructuredOutputError",
    "UnsupportedFeatureError",
]

# Providers
__all__ += [
    "BaseProvider",
    "ProviderCapabilities",
]

# Backends
__all__ += [
    "AnthropicBackend",
    "ChatBackend",
    "OpenAIBackend",
    "OpenRouterBackend",
]
