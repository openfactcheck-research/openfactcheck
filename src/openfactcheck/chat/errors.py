"""Error hierarchy for the chat layer.

Every chat layer error derives from [`ChatModelError`][ChatModelError].
Backend implementations convert SDK-specific exceptions into these types,
so caller code handles a single error surface regardless of which provider
is in use.

Catch the specific subclass you can recover from, or catch
[`ChatModelError`][ChatModelError] to handle every chat-layer failure in
one place.

Example:
    ```python
    from openfactcheck.chat import (
        AuthenticationError,
        ChatClient,
        ChatModelError,
        OpenAIConfig,
        RateLimitError,
        UserMessage,
    )

    client = ChatClient(config=OpenAIConfig(model="gpt-4o"))

    try:
        response = client.completion([UserMessage(content="Hello")])
    except AuthenticationError:
        ...  # fix credentials
    except RateLimitError:
        ...  # back off and retry
    except ChatModelError:
        ...  # everything else
    ```
"""


class ChatModelError(Exception):
    """Base exception for every chat layer error.

    Catch this to handle any failure from [`ChatClient`][ChatClient] without
    branching on the specific cause.
    """


class ProviderNotFoundError(ChatModelError):
    """The requested provider name is not registered or its SDK is not installed.

    Raised when [`ChatClient`][ChatClient] is constructed with a
    [`ModelConfig`][ModelConfig] whose provider has no registered
    [`BaseProvider`][BaseProvider], or when a backend's optional SDK
    dependency is missing from the environment (install with
    ``pip install 'openfactcheck[openai]'``, ``openfactcheck[anthropic]``,
    and so on).
    """


class AuthenticationError(ChatModelError):
    """Credentials are missing, invalid, or expired.

    Typically surfaces when the provider's API key environment variable is
    unset, or when the key has since been revoked. Consult the provider's
    documentation for the expected environment variable.
    """


class RateLimitError(ChatModelError):
    """The provider's rate limit was exceeded.

    Back off and retry. The provider often reports a retry-after window in
    the underlying response; consult the provider's documentation for the
    exact policy.
    """


class ProviderError(ChatModelError):
    """Provider returned an error that doesn't map to a more specific type.

    A catch-all for unexpected status codes, malformed responses, and
    transport failures. Callers usually treat this as non-retriable without
    additional context.
    """


class UnsupportedFeatureError(ChatModelError):
    """The provider does not support a requested feature.

    Raised when a [`ModelConfig`][ModelConfig] or message payload requests
    behavior the provider can't satisfy, for example tool calls on a model
    that doesn't support them.
    """
