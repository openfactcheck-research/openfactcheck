"""Resolve a configured run into a runnable graph.

A run is either a **prebuilt pipeline** named in configuration or a **graph built in code**. This module
covers the first: [`build_prebuilt_graph`][build_prebuilt_graph] resolves the chat and search clients a
pipeline needs from the global configuration and hands them to the pipeline's own graph builder. The chat
client is registered on the given [`AsyncExitStack`][contextlib.AsyncExitStack] so the run closes it when it
finishes. A custom graph built in code needs nothing here; OpenFactCheck runs it directly. Pipelines are
registered by the namespaces themselves; this module names no specific one.
"""

from contextlib import AsyncExitStack
from typing import Any

from pydantic import SecretStr

from openfactcheck.chat import ChatClient
from openfactcheck.components.registry import Pipeline
from openfactcheck.components.types import Input
from openfactcheck.config import ModelSpec, OpenFactCheckConfig, RuntimeSpec
from openfactcheck.graph import Graph
from openfactcheck.integrations.serper import SerperClient, SerperSpec


def resolve_chat_client(
    model: ModelSpec,
    runtime: RuntimeSpec,
    *,
    fallback_name: str | None,
    global_runtime: RuntimeSpec,
    stack: AsyncExitStack,
) -> ChatClient:
    """Build a chat client from a model and runtime spec, registering it for cleanup.

    Args:
        model: The model spec.
        runtime: The runtime spec.
        fallback_name: Model name used when the spec sets none (the global model, then the pipeline default).
        global_runtime: The run's runtime defaults, which ``runtime`` overrides field by field.
        stack: The exit stack the client's close is registered on.

    Returns:
        A chat client for the resolved model and runtime.
    """
    model_config = model.to_model_config(fallback_name=fallback_name)
    runtime_config = runtime.merged_over(global_runtime).to_runtime_config()
    client = ChatClient(model_config, runtime_config)
    stack.push_async_callback(client.aclose)
    return client


def resolve_serper_client(serper: SerperSpec, *, fallback_api_key: SecretStr) -> SerperClient:
    """Build a search client from a Serper spec.

    Args:
        serper: The Serper spec.
        fallback_api_key: API key used when the spec sets none.

    Returns:
        A Serper client for the resolved key, locale, and timeout.
    """
    return serper.to_client(fallback_api_key=fallback_api_key)


def build_prebuilt_graph(
    pipeline: Pipeline, config: OpenFactCheckConfig, *, stack: AsyncExitStack
) -> Graph[Input, Any, None, None]:
    """Build a prebuilt pipeline's graph with the global model and Serper settings applied.

    Args:
        pipeline: The prebuilt pipeline to build.
        config: The run configuration, for the global model (with its sampling) and Serper key.
        stack: The exit stack the chat client is registered on.

    Returns:
        The pipeline's runnable graph.
    """
    model = config.model if isinstance(config.model, ModelSpec) else ModelSpec(name=config.model)
    chat = resolve_chat_client(
        model,
        RuntimeSpec(),
        fallback_name=pipeline.default_model,
        global_runtime=config.runtime,
        stack=stack,
    )
    serper = resolve_serper_client(SerperSpec(), fallback_api_key=config.serper_api_key)
    return pipeline.build_graph(chat=chat, serper=serper)
