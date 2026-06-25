"""The top-level fact-checking entry point.

[`OpenFactCheck`][OpenFactCheck] runs a fact-checking graph: either a prebuilt pipeline named in
configuration, or a graph built and passed directly. A directly-supplied graph overrides the configured
pipeline. The synchronous methods wrap their asynchronous peers; [`stream`][OpenFactCheck.stream] /
[`astream`][OpenFactCheck.astream] surface progress events as the run proceeds. A run returns the graph's raw
output: a list of verdicts for a linear pipeline, a research result, or whatever a directly-supplied graph
produces.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack
from typing import Any, Literal

from openfactcheck.components.registry import Pipeline, get_pipeline
from openfactcheck.components.types import Input
from openfactcheck.config import OpenFactCheckConfig
from openfactcheck.graph import Graph, GraphEvent, RunOptions
from openfactcheck.resolve import build_prebuilt_graph

type _Mode = Literal["graph", "prebuilt"]
type _RunGraph = Graph[Input, Any, None, None]
"""A graph OpenFactCheck runs: input text in, the graph's own output out. The output is typed ``Any`` because a
run yields whatever the graph produces and is not mapped further here."""


class OpenFactCheck:
    """Run a fact-checking pipeline from configuration, or a graph built directly.

    Pass a `graph` to run it directly, or leave it unset and let the configuration's `pipeline` name a
    prebuilt pipeline; a `graph` overrides the configured pipeline. Then [`run`][OpenFactCheck.run] it (or
    [`arun`][OpenFactCheck.arun] from inside an event loop), or stream its progress with
    [`stream`][OpenFactCheck.stream] / [`astream`][OpenFactCheck.astream].

    Example:
        ```python
        from openfactcheck import OpenFactCheck

        ofc = OpenFactCheck()  # loads openfactcheck.yaml or the environment; runs config.pipeline
        verdicts = ofc.run("The Eiffel Tower opened in 1889.")
        ```
    """

    def __init__(self, config: OpenFactCheckConfig | None = None, *, graph: _RunGraph | None = None) -> None:
        """Configure the run.

        Args:
            config: The run configuration. Loaded from the environment and config files when omitted.
            graph: A graph to run directly. Overrides the configured pipeline when given.

        Raises:
            ValueError: If no graph is given and the configuration names no pipeline.
        """
        self._config = config if config is not None else OpenFactCheckConfig()
        self._graph = graph
        self._pipeline: Pipeline | None = None
        self._mode: _Mode = self._resolve_mode()

    def _resolve_mode(self) -> _Mode:
        """Decide how the run is configured; a directly-supplied graph wins over the configured pipeline."""
        if self._graph is not None:
            return "graph"
        if self._config.pipeline is not None:
            self._pipeline = get_pipeline(self._config.pipeline)
            return "prebuilt"
        raise ValueError("nothing to run: pass a graph, or set `pipeline` in the configuration to a prebuilt name.")

    def _build_graph(self, stack: AsyncExitStack) -> _RunGraph:
        """Build the graph for this run, registering any clients it creates on ``stack``."""
        if self._mode == "graph":
            assert self._graph is not None  # noqa: S101 - guaranteed by _resolve_mode.
            return self._graph
        assert self._pipeline is not None  # noqa: S101 - guaranteed by _resolve_mode.
        return build_prebuilt_graph(self._pipeline, self._config, stack=stack)

    async def arun(self, content: str | Input) -> Any:  # noqa: ANN401 - the output type is the graph's, not OpenFactCheck's.
        """Run the configured graph over ``content`` and return its raw output.

        Args:
            content: The text to check, as a string or an [`Input`][openfactcheck.components.types.Input].

        Returns:
            The graph's output: a list of verdicts for a linear pipeline, or the graph's own output otherwise.
        """
        inp = content if isinstance(content, Input) else Input(content=content)
        async with AsyncExitStack() as stack:
            return await self._build_graph(stack).arun(inp, state=None, deps=None)

    def run(self, content: str | Input) -> Any:  # noqa: ANN401 - the output type is the graph's, not OpenFactCheck's.
        """Run the configured graph over ``content`` and return its raw output.

        The synchronous counterpart of [`arun`][OpenFactCheck.arun]; call ``arun`` from inside a running event
        loop.

        Args:
            content: The text to check, as a string or an [`Input`][openfactcheck.components.types.Input].

        Returns:
            The graph's output.
        """
        return asyncio.run(self.arun(content))

    async def astream(self, content: str | Input) -> AsyncIterator[GraphEvent]:
        """Run the fact-check and yield progress events as they happen.

        Yields a start and finish event per node, with node-level data events in between, then a final
        run-finished event.

        Args:
            content: The text to check, as a string or an [`Input`][openfactcheck.components.types.Input].

        Yields:
            Each [`GraphEvent`][openfactcheck.graph.GraphEvent] in turn.
        """
        inp = content if isinstance(content, Input) else Input(content=content)
        async with AsyncExitStack() as stack:
            graph = self._build_graph(stack)
            async for event in graph.astream(inp, state=None, deps=None, options=RunOptions(stream_node_data=True)):
                yield event

    def stream(self, content: str | Input) -> Iterator[GraphEvent]:
        """Run the fact-check and return its progress events.

        The synchronous counterpart of [`astream`][OpenFactCheck.astream]; it runs to completion and returns
        the events. Call ``astream`` for events as they arrive.

        Args:
            content: The text to check, as a string or an [`Input`][openfactcheck.components.types.Input].

        Returns:
            An iterator over the run's [`GraphEvent`][openfactcheck.graph.GraphEvent] values.
        """

        async def collect() -> list[GraphEvent]:
            return [event async for event in self.astream(content)]

        return iter(asyncio.run(collect()))
