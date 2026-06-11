"""Tests for OpenRouterBackend with mocked openai SDK.

The four call shapes are inherited unchanged from OpenAIBackend and covered
by its tests; these cover only the OpenRouter-specific behavior: key
resolution and pointing the SDK client at OpenRouter's endpoint.
"""

from types import SimpleNamespace

import pytest

from openfactcheck.chat.backends.openrouter import OpenRouterBackend
from openfactcheck.chat.backends.openrouter.backend import OPENROUTER_BASE_URL
from openfactcheck.chat.config import OpenRouterConfig, RuntimeConfig
from openfactcheck.chat.errors import AuthenticationError
from openfactcheck.chat.messages import UserMessage
from openfactcheck.chat.requests import ChatRequest


def _build_request() -> ChatRequest:
    return ChatRequest(
        messages=[UserMessage(content="Hi")],
        config=OpenRouterConfig(model="openai/gpt-4o"),
        runtime=RuntimeConfig(),
    )


def _fake_response() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Hello!", tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
    )


def _patch_sync_client(mocker) -> object:  # noqa: ANN001
    """Mock the sync OpenAI client and return the client class mock."""
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=mocker.MagicMock(return_value=_fake_response())),
        ),
    )
    mock_cls = mocker.MagicMock(return_value=mock_client)
    mocker.patch("openfactcheck.chat.backends.openai.backend.load_openai", return_value=mock_cls)
    return mock_cls


def test_OpenRouterBackend_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing OPENROUTER_API_KEY raises AuthenticationError at construction."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(AuthenticationError, match="OPENROUTER_API_KEY"):
        OpenRouterBackend()


def test_OpenRouterBackend_completion_targets_openrouter(mocker, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    """completion builds the SDK client with OpenRouter's base URL and env key."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-env")
    mock_cls = _patch_sync_client(mocker)
    backend = OpenRouterBackend()

    response = backend.completion(_build_request())

    assert response.message.content == "Hello!"
    assert response.provider == "openrouter"
    client_kwargs = mock_cls.call_args.kwargs
    assert client_kwargs["base_url"] == OPENROUTER_BASE_URL
    assert client_kwargs["api_key"] == "sk-env"


def test_OpenRouterBackend_explicit_key_overrides_env(mocker, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    """An explicit api_key takes precedence over the environment variable."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-env")
    mock_cls = _patch_sync_client(mocker)
    backend = OpenRouterBackend(api_key="sk-explicit")

    backend.completion(_build_request())

    assert mock_cls.call_args.kwargs["api_key"] == "sk-explicit"
