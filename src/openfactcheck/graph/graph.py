"""The built graph and its executor.

A [`Graph`][Graph] is the runnable artifact produced by
[`GraphBuilder.build`][GraphBuilder]. It runs nodes by draining a work queue:
the start edge seeds the queue with the graph input, each node runs and its
outgoing edges enqueue the node's output for its successors, and the value
routed into the end node is the run's result.

The async [`arun`][Graph.arun] is the native entry point; the sync
[`run`][Graph.run] wraps it for scripts and notebooks.
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING, cast

from openfactcheck.graph.errors import GraphRuntimeError
from openfactcheck.graph.step import StepContext

if TYPE_CHECKING:
    from openfactcheck.graph.step import AnyStep, Edge

_UNSET: object = object()
"""Sentinel for "the end node was never reached"."""


class Graph[StateT, DepsT, InputT, OutputT]:
    """An executable graph of typed nodes.

    Assembled by [`GraphBuilder.build`][GraphBuilder]; construct it through the
    builder rather than directly. Run it with [`run`][Graph.run] or its async
    peer [`arun`][Graph.arun].
    """

    def __init__(
        self,
        *,
        steps: dict[str, AnyStep],
        edges_by_source: dict[str, list[Edge]],
        start_id: str,
        end_id: str,
        name: str,
    ) -> None:
        """Record the validated nodes and edges of a built graph.

        Args:
            steps: Work-bearing nodes keyed by id.
            edges_by_source: Outgoing edges grouped by their source node id.
            start_id: Identifier of the start node.
            end_id: Identifier of the end node.
            name: Human-readable name for diagrams and logs.
        """
        self._steps = steps
        self._edges_by_source = edges_by_source
        self._start_id = start_id
        self._end_id = end_id
        self.name = name

    async def arun(self, inputs: InputT, *, state: StateT, deps: DepsT) -> OutputT:
        """Run the graph to completion and return its terminal output.

        Args:
            inputs: The value handed to the first node.
            state: Run-scoped state shared across nodes.
            deps: Run-scoped dependencies injected into nodes.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
        """
        queue: deque[tuple[str, object]] = deque(
            (edge.dest_id, inputs) for edge in self._edges_by_source.get(self._start_id, [])
        )
        final: object = _UNSET
        while queue:
            node_id, value = queue.popleft()
            if node_id == self._end_id:
                final = value
                continue
            step = self._steps[node_id]
            output = await step.call(StepContext(inputs=value, state=state, deps=deps))
            for edge in self._edges_by_source[node_id]:
                queue.append((edge.dest_id, output))
        if final is _UNSET:
            raise GraphRuntimeError("run finished without reaching the end node")
        return cast("OutputT", final)

    def run(self, inputs: InputT, *, state: StateT, deps: DepsT) -> OutputT:
        """Run the graph to completion synchronously.

        A blocking wrapper over [`arun`][Graph.arun] for scripts and notebooks.
        Call ``arun`` directly from inside a running event loop.

        Args:
            inputs: The value handed to the first node.
            state: Run-scoped state shared across nodes.
            deps: Run-scoped dependencies injected into nodes.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
        """
        return asyncio.run(self.arun(inputs, state=state, deps=deps))
