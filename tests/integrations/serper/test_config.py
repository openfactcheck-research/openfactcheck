"""Tests for SerperSpec and its client builder."""

import pytest
from pydantic import SecretStr

from openfactcheck.integrations.serper import SerperClient, SerperConfigError, SerperSpec


def test_SerperSpec_to_client_applies_settings() -> None:
    """The spec's key, locale, and timeout flow into the built client."""
    client = SerperSpec(api_key=SecretStr("test-key"), gl="us", hl="en", timeout=12.0).to_client()

    assert isinstance(client, SerperClient)
    assert client._gl == "us"
    assert client._hl == "en"
    assert client._timeout == 12.0


def test_SerperSpec_to_client_uses_fallback_key() -> None:
    """An unset key falls back to the one supplied at build time."""
    client = SerperSpec().to_client(fallback_api_key=SecretStr("fallback-key"))

    assert client._api_key == "fallback-key"


def test_SerperSpec_to_client_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no key in the spec, the fallback, or the environment, building raises."""
    monkeypatch.delenv("SERPER_API_KEY", raising=False)

    with pytest.raises(SerperConfigError):
        SerperSpec().to_client()
