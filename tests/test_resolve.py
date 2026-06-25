"""Tests for resolve: resolving clients and building a prebuilt pipeline's graph."""

import os
from contextlib import AsyncExitStack
from pathlib import Path

import pytest
from pydantic import SecretStr

from openfactcheck.chat import ChatClient
from openfactcheck.components.registry import get_pipeline
from openfactcheck.config import ModelSpec, OpenFactCheckConfig, RuntimeSpec
from openfactcheck.graph import Graph
from openfactcheck.integrations.serper import SerperClient, SerperSpec
from openfactcheck.resolve import build_prebuilt_graph, resolve_chat_client, resolve_serper_client


@pytest.fixture(autouse=True)
def _clean_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate each test from ambient config: no OpenFactCheck env vars, a clean working directory."""
    for key in list(os.environ):
        if key.startswith("OPENFACTCHECK_") or key == "SERPER_API_KEY":
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


def test_resolve_chat_client_uses_the_fallback_model() -> None:
    """A chat client builds on the fallback model name when the spec sets none."""
    client = resolve_chat_client(
        ModelSpec(),
        RuntimeSpec(),
        fallback_name="openai/gpt-4o-mini",
        global_runtime=RuntimeSpec(),
        stack=AsyncExitStack(),
    )

    assert isinstance(client, ChatClient)


def test_resolve_serper_client_builds_with_a_key() -> None:
    """A search client builds from a spec carrying an API key."""
    client = resolve_serper_client(SerperSpec(api_key=SecretStr("test-key")), fallback_api_key=SecretStr(""))

    assert isinstance(client, SerperClient)


def test_build_prebuilt_graph_builds_a_named_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """A prebuilt pipeline resolves by name into a runnable graph (with a Serper key present)."""
    monkeypatch.setenv("SERPER_API_KEY", "test-key")

    graph = build_prebuilt_graph(get_pipeline("factool"), OpenFactCheckConfig(), stack=AsyncExitStack())

    assert isinstance(graph, Graph)
