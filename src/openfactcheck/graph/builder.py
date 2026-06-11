"""Assemble and validate a typed graph from steps and edges.

[`GraphBuilder`][GraphBuilder] collects work-bearing [`Step`][Step] nodes and
the edges between them, then [`build`][GraphBuilder.build] validates the
structure and returns a runnable [`Graph`][Graph].

Example:
    ```python
    g = GraphBuilder[None, None, str, dict]()


    @g.step
    async def extract(ctx: StepContext[None, None, str]) -> list[str]:
        return ctx.inputs.split()


    @g.step
    async def count(ctx: StepContext[None, None, list[str]]) -> dict:
        return {"n": len(ctx.inputs)}


    g.add(
        g.edge_from(g.start_node).to(extract),
        g.edge_from(extract).to(count),
        g.edge_from(count).to(g.end_node),
    )
    graph = g.build()
    result = graph.run("a b c", state=None, deps=None)
    ```
"""

from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import get_args, get_type_hints

from openfactcheck.graph.errors import GraphBuildError, GraphValidationError
from openfactcheck.graph.graph import Graph
from openfactcheck.graph.step import (
    END_ID,
    START_ID,
    AnyStep,
    DestNode,
    Edge,
    EndNode,
    SourceNode,
    StartNode,
    Step,
    StepContext,
)

_STEP_CONTEXT_ARITY = 3
"""Number of type arguments on ``StepContext[State, Deps, Input]``."""


@dataclass(frozen=True, slots=True)
class EdgeBuilder:
    """A partially-built edge, awaiting its destination.

    Returned by [`GraphBuilder.edge_from`][GraphBuilder.edge_from]; call
    [`to`][EdgeBuilder.to] to name the destination and produce an
    [`Edge`][Edge].
    """

    source_id: str
    """Identifier of the node the edge will leave."""

    def to(self, dest: DestNode) -> Edge:
        """Complete the edge by naming its destination node.

        Args:
            dest: The node the edge enters.

        Returns:
            The finished edge from the recorded source to ``dest``.
        """
        return Edge(source_id=self.source_id, dest_id=dest.id)


class GraphBuilder[StateT, DepsT, InputT, OutputT]:
    """Collect steps and edges, then build a validated [`Graph`][Graph].

    Parameterized by the run-scoped state and dependency types and the graph's
    overall input and output types. The state and dependency types flow into
    every [`StepContext`][StepContext]; the input and output types describe the
    values the built graph accepts and returns.
    """

    def __init__(self, *, name: str = "graph") -> None:
        """Start an empty builder.

        Args:
            name: Human-readable name carried onto the built graph for
                diagrams and logs.
        """
        self._name = name
        self._steps: dict[str, AnyStep] = {}
        self._edges: list[Edge] = []
        self.start_node = StartNode()
        self.end_node = EndNode()

    def step[StepInputT, StepOutputT](
        self,
        call: Callable[[StepContext[StateT, DepsT, StepInputT]], Awaitable[StepOutputT]],
    ) -> Step[StateT, DepsT, StepInputT, StepOutputT]:
        """Register an async function as a node and return it for wiring.

        Usually applied as the ``@g.step`` decorator. The node's id is the
        function's name; its input and output types are read from the function's
        annotations for build-time edge validation.

        Args:
            call: An async function taking a [`StepContext`][StepContext] and
                returning this node's output.

        Returns:
            The registered [`Step`][Step], used as a source or destination when
            wiring edges.

        Raises:
            GraphBuildError: If a step with the same id is already registered.
        """
        input_type, output_type = self._io_types(call)
        node = Step(id=call.__name__, call=call, input_type=input_type, output_type=output_type)
        if node.id in self._steps:
            raise GraphBuildError(f"duplicate step id {node.id!r}")
        self._steps[node.id] = node
        return node

    def edge_from(self, source: SourceNode) -> EdgeBuilder:
        """Begin an edge leaving ``source``.

        Args:
            source: The step or start node the edge leaves.

        Returns:
            A builder whose [`to`][EdgeBuilder.to] names the destination.
        """
        return EdgeBuilder(source.id)

    def add(self, *edges: Edge) -> None:
        """Register one or more edges into the graph being built.

        Args:
            edges: Edges produced by [`edge_from`][GraphBuilder.edge_from].
        """
        self._edges.extend(edges)

    def build(self) -> Graph[StateT, DepsT, InputT, OutputT]:
        """Validate the assembled graph and return a runnable [`Graph`][Graph].

        Returns:
            The validated, runnable graph.

        Raises:
            GraphBuildError: If an edge references an unknown node or a step id
                is duplicated.
            GraphValidationError: If the graph has no entry or exit, has
                unreachable nodes or dead-ends, or connects incompatible types.
        """
        edges_by_source = self._index_edges()
        self._validate_endpoints(edges_by_source)
        self._validate_reachability(edges_by_source)
        self._validate_edge_types()
        return Graph(
            steps=self._steps,
            edges_by_source=edges_by_source,
            start_id=START_ID,
            end_id=END_ID,
            name=self._name,
        )

    def _index_edges(self) -> dict[str, list[Edge]]:
        """Group edges by source after checking that every endpoint is known."""
        node_ids = {START_ID, END_ID, *self._steps}
        edges_by_source: dict[str, list[Edge]] = {}
        for edge in self._edges:
            if edge.source_id not in node_ids:
                raise GraphBuildError(f"edge from unknown node {edge.source_id!r}")
            if edge.dest_id not in node_ids:
                raise GraphBuildError(f"edge to unknown node {edge.dest_id!r}")
            edges_by_source.setdefault(edge.source_id, []).append(edge)
        return edges_by_source

    def _validate_endpoints(self, edges_by_source: dict[str, list[Edge]]) -> None:
        """Check that the start, end, and every step are wired in."""
        if START_ID not in edges_by_source:
            raise GraphValidationError("graph has no entry edge from the start node")
        if all(edge.dest_id != END_ID for edge in self._edges):
            raise GraphValidationError("graph has no edge into the end node")
        for step_id in self._steps:
            if step_id not in edges_by_source:
                raise GraphValidationError(f"node {step_id!r} has no outgoing edge")

    def _validate_reachability(self, edges_by_source: dict[str, list[Edge]]) -> None:
        """Check that every step and the end node are reachable from the start."""
        seen: set[str] = set()
        queue = deque([START_ID])
        while queue:
            node_id = queue.popleft()
            for edge in edges_by_source.get(node_id, []):
                if edge.dest_id not in seen:
                    seen.add(edge.dest_id)
                    queue.append(edge.dest_id)
        unreachable = sorted(set(self._steps) - seen)
        if unreachable:
            raise GraphValidationError(f"nodes are not reachable from the start node: {unreachable}")
        if END_ID not in seen:
            raise GraphValidationError("the end node is not reachable from the start node")

    def _validate_edge_types(self) -> None:
        """Raise if any step-to-step edge connects an incompatible output and input.

        Edges touching the start or end node are skipped, as those carry no
        captured type.

        Raises:
            GraphValidationError: If a known output type does not match the
                known input type of the node it feeds.
        """
        for edge in self._edges:
            src = self._steps.get(edge.source_id)
            dst = self._steps.get(edge.dest_id)
            if src is None or dst is None:
                continue
            if src.output_type is None or dst.input_type is None:
                continue
            if src.output_type != dst.input_type:
                raise GraphValidationError(
                    f"edge {edge.source_id!r} -> {edge.dest_id!r}: output type {src.output_type!r} "
                    f"does not match input type {dst.input_type!r}",
                )

    @staticmethod
    def _io_types(call: Callable[..., object]) -> tuple[object | None, object | None]:
        """Read a step function's declared input and output types from its annotations.

        Args:
            call: The step function to inspect.

        Returns:
            A pair ``(input_type, output_type)``; either element is ``None``
            when the corresponding annotation is absent or not a
            ``StepContext``.
        """
        hints = get_type_hints(call)
        output_type = hints.get("return")
        input_type: object | None = None
        for name, hint in hints.items():
            if name == "return":
                continue
            args = get_args(hint)
            if len(args) == _STEP_CONTEXT_ARITY:
                input_type = args[2]
            break
        return input_type, output_type
