"""Tests for LLM error hierarchy."""

import pytest

from openfactcheck.chat.errors import (
    AuthenticationError,
    ChatModelError,
    ProviderError,
    ProviderNotFoundError,
    RateLimitError,
    UnsupportedFeatureError,
)


@pytest.mark.parametrize(
    "error_cls",
    [
        ProviderNotFoundError,
        AuthenticationError,
        RateLimitError,
        ProviderError,
        UnsupportedFeatureError,
    ],
    ids=lambda cls: cls.__name__,
)
def test_error_inherits_from_base(error_cls: type[ChatModelError]) -> None:
    """All errors inherit from ChatModelError."""
    err = error_cls("test message")

    assert isinstance(err, ChatModelError)
    assert isinstance(err, Exception)
    assert str(err) == "test message"
