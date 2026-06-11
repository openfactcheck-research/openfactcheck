"""Tests for LLM error hierarchy."""

import pytest
from pydantic import BaseModel, ValidationError

from openfactcheck.chat.errors import (
    AuthenticationError,
    ChatModelError,
    ProviderError,
    ProviderNotFoundError,
    RateLimitError,
    StructuredOutputError,
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


def test_StructuredOutputError_carries_raw_and_validation_error() -> None:
    """StructuredOutputError is a ChatModelError and exposes the raw reply and validation error."""

    class _Model(BaseModel):
        count: int

    try:
        _Model.model_validate_json("{}")
    except ValidationError as exc:
        err = StructuredOutputError("did not match", raw="{}", validation_error=exc)

    assert isinstance(err, ChatModelError)
    assert err.raw == "{}"
    assert isinstance(err.validation_error, ValidationError)
