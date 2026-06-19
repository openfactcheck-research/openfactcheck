"""Assemble and validate a typed graph from steps and edges.

[`GraphBuilder`][GraphBuilder] collects work-bearing [`Step`][Step] nodes and
the edges between them, then [`build`][GraphBuilder.build] validates the
structure and returns a runnable [`Graph`][Graph].

Example:
    ```python
    g = GraphBuilder(input_type=str, output_type=dict)


    @g.step_node
    async def extract(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()


    @g.step_node
    async def count(ctx: StepContext[list[str]]) -> dict:
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

from __future__ import annotations

import inspect
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, get_args, get_type_hints, overload

from openfactcheck.graph._typevars import DepsT, InputT, OutputT, StateT
from openfactcheck.graph.decision import Branch, Decision
from openfactcheck.graph.errors import GraphBuildError, GraphValidationError
from openfactcheck.graph.graph import Graph, GraphSpec
from openfactcheck.graph.join import Join, reduce_list_append
from openfactcheck.graph.pause import Pause
from openfactcheck.graph.step import (
    END_ID,
    START_ID,
    AnyStep,
    DestNode,
    Edge,
    EdgeKind,
    EndNode,
    SourceNode,
    StartNode,
    Step,
    StepContext,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from openfactcheck.graph.decision import AnyDecision
    from openfactcheck.graph.join import AnyJoin, ContextReducer, NormalizedReducer, Reducer, ReducerContext
    from openfactcheck.graph.pause import AnyPause

_STEP_CONTEXT_ARITY = 3
"""Number of type arguments on ``StepContext[Input, State, Deps]``."""

_PLAIN_REDUCER_ARITY = 2
"""Parameter count of a plain ``(accumulator, value)`` reducer."""

_CONTEXT_REDUCER_ARITY = 3
"""Parameter count of a ``(context, accumulator, value)`` reducer."""


@dataclass(frozen=True, slots=True)
class _InlineJoinSpec:
    """A fan-in declared inline on an edge via collect/reduce, before the builder expands it into a join."""

    verb: str
    reducer: Callable[..., object]
    initial_factory: Callable[[], object]
    ordered: bool


@dataclass(frozen=True, slots=True)
class _InlineJoinEdge:
    """An edge routed through an inline join; the builder expands it into a join node and two edges."""

    source_id: str
    dest_id: str
    spec: _InlineJoinSpec


@dataclass(frozen=True, slots=True)
class EdgePathBuilder[OutputT, StateT, DepsT]:
    """A partially-built edge, awaiting its destination.

    Returned by [`GraphBuilder.edge_from`][GraphBuilder.edge_from], carrying the
    output type of its source node so [`to`][EdgePathBuilder.to] only accepts a
    destination whose input type the source can feed. A mismatched destination
    is a type error, caught before the graph is built.
    """

    source_id: str
    """Identifier of the node the edge will leave."""

    kind: EdgeKind = EdgeKind.PLAIN
    """Whether the edge delivers the whole output or fans an iterable per item."""

    join: _InlineJoinSpec | None = None
    """A fan-in folded onto this edge by [`collect`][EdgePathBuilder.collect] or [`reduce`][EdgePathBuilder.reduce]."""

    def map[ItemT](
        self: EdgePathBuilder[Iterable[ItemT], StateT, DepsT],
    ) -> EdgePathBuilder[ItemT, StateT, DepsT]:
        """Fan the source's iterable output out to one parallel branch per item.

        Available only when the source node's output is iterable. The chosen
        destination then receives a single item, and a downstream
        [`Join`][Join] collects the per-item results. Run concurrency is bounded
        by [`Graph.arun`][Graph.arun]'s ``concurrency`` limit.

        Returns:
            A builder over the collection's item type whose
            [`to`][EdgePathBuilder.to] names the per-item destination.
        """
        return EdgePathBuilder(self.source_id, kind=EdgeKind.MAP)

    def collect[CollectItemT](
        self: EdgePathBuilder[CollectItemT, StateT, DepsT],
    ) -> EdgePathBuilder[list[CollectItemT], StateT, DepsT]:
        """Gather a fork's branch outputs into one ordered list, inline on the edge.

        The mirror of [`map`][EdgePathBuilder.map]: where ``map`` fans an
        iterable out to one branch per item, ``collect`` folds those branches
        back into a single list in source order and delivers it to the
        destination. It builds the fan-in join for you, so the destination
        receives ``list[item]`` with no separately declared
        [`collect_node`][GraphBuilder.collect_node]; reach for that explicit form
        when a join gathers several distinct inbound edges.

        Returns:
            A builder over the collected list type whose
            [`to`][EdgePathBuilder.to] names the destination that receives it.
        """
        return EdgePathBuilder(
            self.source_id,
            join=_InlineJoinSpec(verb="collect", reducer=reduce_list_append, initial_factory=list, ordered=True),
        )

    def reduce[ReduceItemT, AccT](
        self: EdgePathBuilder[ReduceItemT, StateT, DepsT],
        reducer: Reducer[AccT, ReduceItemT] | ContextReducer[StateT, DepsT, AccT, ReduceItemT],
        initial_factory: Callable[[], AccT],
    ) -> EdgePathBuilder[AccT, StateT, DepsT]:
        """Fold a fork's branch outputs with a reducer, inline on the edge.

        The general fan-in that [`collect`][EdgePathBuilder.collect] specializes:
        each branch's value folds into a running accumulator, and the final
        accumulator is delivered to the destination. It builds the fan-in join
        for you; reach for [`reduce_node`][GraphBuilder.reduce_node] when a join
        gathers several distinct inbound edges.

        Args:
            reducer: The fold applied to each branch's value, taking the running
                accumulator and one value, optionally preceded by a
                [`ReducerContext`][ReducerContext].
            initial_factory: Builds the accumulator each time the join fires.

        Returns:
            A builder over the accumulator type whose
            [`to`][EdgePathBuilder.to] names the destination that receives it.
        """
        return EdgePathBuilder(
            self.source_id,
            join=_InlineJoinSpec(verb="reduce", reducer=reducer, initial_factory=initial_factory, ordered=False),
        )

    def to(self, dest: DestNode[OutputT, StateT, DepsT]) -> Edge | _InlineJoinEdge:
        """Complete the edge by naming its destination node.

        Args:
            dest: The node the edge enters; its input type must accept the
                source node's output type.

        Returns:
            The finished edge from the recorded source to ``dest``, or, when
            [`collect`][EdgePathBuilder.collect] or [`reduce`][EdgePathBuilder.reduce]
            folded a fan-in onto this edge, a token the builder expands into the
            inline join and its two edges.
        """
        if self.join is not None:
            return _InlineJoinEdge(source_id=self.source_id, dest_id=dest.id, spec=self.join)
        return Edge(source_id=self.source_id, dest_id=dest.id, kind=self.kind)


class GraphBuilder(Generic[InputT, OutputT, StateT, DepsT]):
    """Collect steps and edges, then build a validated [`Graph`][Graph].

    Construct it the named way, ``GraphBuilder(input_type=..., output_type=...)``,
    or with positional type parameters, ``GraphBuilder[Input, Output]``. The type
    parameters, in order, are:

    1. ``InputT``: the value the built graph accepts.
    2. ``OutputT``: the value the built graph returns.
    3. ``StateT``: run-scoped mutable state shared across every node. Optional;
       defaults to ``None`` (no shared state).
    4. ``DepsT``: read-only dependencies injected into every node (clients,
       configuration). Optional; defaults to ``None`` (no deps).

    ``StateT`` and ``DepsT`` flow unchanged into every
    [`StepContext`][StepContext].

    Example:
        ```python
        # str in, a dict out, no shared state, a Deps bag of clients.
        g = GraphBuilder(input_type=str, output_type=dict[str, int], deps_type=Deps)
        # the positional form is equivalent: GraphBuilder[str, dict[str, int], None, Deps]
        ```
    """

    def __init__(
        self,
        *,
        input_type: type[InputT] | None = None,
        output_type: type[OutputT] | None = None,
        state_type: type[StateT] | None = None,
        deps_type: type[DepsT] | None = None,
        name: str = "graph",
    ) -> None:
        """Start an empty builder.

        The four ``*_type`` arguments are optional and bind the builder's type
        parameters by name; ``state_type`` and ``deps_type`` default to ``None``.
        They are recorded for introspection and are not required at run time.

        Args:
            input_type: The type the built graph accepts.
            output_type: The type the built graph returns.
            state_type: The run-scoped state type, or ``None`` for no state.
            deps_type: The injected dependencies type, or ``None`` for no deps.
            name: Human-readable name carried onto the built graph for
                diagrams and logs.
        """
        self._name = name
        self._input_type = input_type
        self._output_type = output_type
        self._state_type = state_type
        self._deps_type = deps_type
        self._steps: dict[str, AnyStep] = {}
        self._joins: dict[str, AnyJoin] = {}
        self._decisions: dict[str, AnyDecision] = {}
        self._pauses: dict[str, AnyPause] = {}
        self._edges: list[Edge] = []
        self._branches: list[Branch] = []
        self.start_node: StartNode[InputT] = StartNode()
        self.end_node: EndNode[OutputT] = EndNode()

    @overload
    def step_node[StepInputT, StepOutputT](
        self,
        call: Callable[[StepContext[StepInputT, StateT, DepsT]], Awaitable[StepOutputT]],
        *,
        node_id: str | None = None,
        retries: int = 0,
        retry_backoff: float = 0.0,
        timeout: float | None = None,
    ) -> Step[StepInputT, StepOutputT, StateT, DepsT]: ...

    @overload
    def step_node[StepInputT, StepOutputT](
        self,
        call: None = None,
        *,
        node_id: str | None = None,
        retries: int = 0,
        retry_backoff: float = 0.0,
        timeout: float | None = None,
    ) -> Callable[
        [Callable[[StepContext[StepInputT, StateT, DepsT]], Awaitable[StepOutputT]]],
        Step[StepInputT, StepOutputT, StateT, DepsT],
    ]: ...

    def step_node[StepInputT, StepOutputT](
        self,
        call: Callable[[StepContext[StepInputT, StateT, DepsT]], Awaitable[StepOutputT]] | None = None,
        *,
        node_id: str | None = None,
        retries: int = 0,
        retry_backoff: float = 0.0,
        timeout: float | None = None,
    ) -> (
        Step[StepInputT, StepOutputT, StateT, DepsT]
        | Callable[
            [Callable[[StepContext[StepInputT, StateT, DepsT]], Awaitable[StepOutputT]]],
            Step[StepInputT, StepOutputT, StateT, DepsT],
        ]
    ):
        """Register an async function as a node and return it for wiring.

        Apply it as a bare decorator, ``@g.step_node`` (the node's id is the
        function's name); as a decorator with options,
        ``@g.step_node(node_id="verify", retries=3)``; or call it directly,
        ``g.step_node(fn, node_id="verify")``. The input and output types are
        read from the function's annotations for build-time edge validation.

        Args:
            call: The async function to register, or ``None`` to return a
                decorator that registers the function it is applied to.
            node_id: Identifier for the node; defaults to the function's name.
            retries: Extra attempts after the first if the call fails.
            retry_backoff: Base seconds before a retry; doubles each attempt.
            timeout: Seconds a single attempt may run, or ``None`` for no limit.

        Returns:
            The registered [`Step`][Step] when ``call`` is given, otherwise a
            decorator that registers its function and returns the step.

        Raises:
            GraphBuildError: If a step with the same id is already registered,
                or an option is out of range.
        """
        if retries < 0 or retry_backoff < 0:
            raise GraphBuildError("retries and retry_backoff must be non-negative")
        if timeout is not None and timeout <= 0:
            raise GraphBuildError("timeout must be positive when set")

        def register(
            fn: Callable[[StepContext[StepInputT, StateT, DepsT]], Awaitable[StepOutputT]],
        ) -> Step[StepInputT, StepOutputT, StateT, DepsT]:
            input_type, output_type = self._io_types(fn)
            node = Step(
                id=node_id or fn.__name__,
                call=fn,
                input_type=input_type,
                output_type=output_type,
                retries=retries,
                retry_backoff=retry_backoff,
                timeout=timeout,
            )
            if self._id_taken(node.id):
                raise GraphBuildError(f"duplicate node id {node.id!r}")
            self._steps[node.id] = node
            return node

        if call is None:
            return register
        return register(call)

    def _id_taken(self, node_id: str) -> bool:
        """Whether a node id is already registered as a step, join, decision, or pause."""
        return node_id in self._steps or node_id in self._joins or node_id in self._decisions or node_id in self._pauses

    def subgraph_node[SubInputT, SubOutputT](
        self,
        graph: Graph[SubInputT, SubOutputT, StateT, DepsT],
        *,
        node_id: str,
    ) -> Step[SubInputT, SubOutputT, StateT, DepsT]:
        """Wrap a built graph as a node that runs it and forwards its output.

        The inner graph runs with the outer run's state and dependencies, so its
        state and dependency types must match this builder's. Wire the returned
        node like any other; its input and output types are the inner graph's.

        Args:
            graph: A built [`Graph`][Graph] to embed as a node.
            node_id: Identifier for the node; must be unique within the graph.

        Returns:
            A [`Step`][Step] that runs the inner graph.

        Raises:
            GraphBuildError: If the chosen node id is already in use.
        """

        async def run_subgraph(ctx: StepContext[SubInputT, StateT, DepsT]) -> SubOutputT:
            """Run the embedded graph with the outer run's state and dependencies."""
            return await graph.arun(ctx.inputs, state=ctx.state, deps=ctx.deps)

        node: Step[SubInputT, SubOutputT, StateT, DepsT] = Step(
            id=node_id,
            call=run_subgraph,
            input_type=None,
            output_type=None,
        )
        if self._id_taken(node.id):
            raise GraphBuildError(f"duplicate node id {node.id!r}")
        self._steps[node.id] = node
        return node

    def collect_node[ItemT](self, item_type: type[ItemT], *, node_id: str) -> Join[ItemT, list[ItemT]]:
        """Create a fan-in node that gathers each branch's output into an ordered list.

        Wire it as the destination of a fanned-out subpath (the
        [`map`][EdgePathBuilder.map] target's successor) and as the source of
        the edge carrying the collected list. The list preserves the source
        collection's order regardless of the order branches finish in.

        Args:
            item_type: The type of each branch's value, recorded for build-time
                edge validation.
            node_id: Identifier for the join node; must be unique within the graph.

        Returns:
            The registered [`Join`][Join] node, collecting into a list.

        Raises:
            GraphBuildError: If the chosen node id is already in use.
        """
        return self._add_join(
            item_type=item_type,
            reducer=self._normalize_reducer(reduce_list_append),
            initial_factory=list,
            ordered=True,
            verb="collect",
            node_id=node_id,
        )

    def reduce_node[ItemT, AccT](
        self,
        reducer: Reducer[AccT, ItemT] | ContextReducer[StateT, DepsT, AccT, ItemT],
        initial_factory: Callable[[], AccT],
        *,
        item_type: type[ItemT],
        node_id: str,
    ) -> Join[ItemT, AccT]:
        """Create a fan-in node that folds each branch's output with a reducer.

        The reducer takes the running accumulator and one branch's value and
        returns the next accumulator, or takes a
        [`ReducerContext`][ReducerContext] first to read run state and stop
        early. Branches are folded in the order they finish, so a reducer should
        not depend on order; use [`collect_node`][GraphBuilder.collect_node] when
        order matters.

        Args:
            reducer: The fold applied to each branch's value.
            initial_factory: Builds the accumulator each time the join fires.
            item_type: The type of each branch's value, recorded for build-time
                edge validation.
            node_id: Identifier for the join node; must be unique within the graph.

        Returns:
            The registered [`Join`][Join] node.

        Raises:
            GraphBuildError: If the chosen node id is already in use, or the
                reducer takes neither two nor three parameters.
        """
        return self._add_join(
            item_type=item_type,
            reducer=self._normalize_reducer(reducer),
            initial_factory=initial_factory,
            ordered=False,
            verb="reduce",
            node_id=node_id,
        )

    def _add_join(  # noqa: PLR0913 - private keyword-only join registrar
        self,
        *,
        item_type: object,
        reducer: NormalizedReducer,
        initial_factory: Callable[[], object],
        ordered: bool,
        verb: str,
        node_id: str,
        inline: bool = False,
    ) -> AnyJoin:
        """Register a join node under the given id."""
        if self._id_taken(node_id):
            raise GraphBuildError(f"duplicate node id {node_id!r}")
        join: AnyJoin = Join(
            id=node_id,
            verb=verb,
            item_type=item_type,
            reducer=reducer,
            initial_factory=initial_factory,
            ordered=ordered,
            inline=inline,
        )
        self._joins[node_id] = join
        return join

    @staticmethod
    def _normalize_reducer(reducer: Callable[..., object]) -> NormalizedReducer:
        """Wrap a plain ``(accumulator, value)`` reducer to the context-taking form.

        Raises:
            GraphBuildError: If the reducer takes neither two nor three parameters.
        """
        arity = len(inspect.signature(reducer).parameters)
        if arity == _CONTEXT_REDUCER_ARITY:
            return reducer
        if arity == _PLAIN_REDUCER_ARITY:

            def with_context(ctx: ReducerContext[object, object], acc: object, value: object) -> object:  # noqa: ARG001 - context unused for a plain reducer.
                return reducer(acc, value)

            return with_context
        raise GraphBuildError(
            f"reducer must take (accumulator, value) or (context, accumulator, value), got {arity} parameters",
        )

    def decision_node[DecisionInputT](
        self,
        input_type: type[DecisionInputT],
        *,
        node_id: str,
    ) -> Decision[DecisionInputT, StateT, DepsT]:
        """Create a routing node that forwards its input to the first matching branch.

        Wire it as the destination of the edge carrying the value to route, then
        register its branches (from [`Decision.when`][Decision.when] and friends)
        with [`add`][GraphBuilder.add]. A value matching no branch and reaching
        no default branch fails the run.

        Args:
            input_type: The type of value the decision routes, matched against
                the output of the edge feeding it.
            node_id: Identifier for the decision node; must be unique within the graph.

        Returns:
            The registered [`Decision`][Decision] node.

        Raises:
            GraphBuildError: If the chosen node id is already in use.
        """
        if self._id_taken(node_id):
            raise GraphBuildError(f"duplicate node id {node_id!r}")
        decision: Decision[DecisionInputT, StateT, DepsT] = Decision(node_id=node_id, input_type=input_type)
        self._decisions[node_id] = decision
        return decision

    def pause_node[ContextT, AnswerT](
        self,
        context_type: type[ContextT],
        answer_type: type[AnswerT],
        *,
        node_id: str,
        prompt: str | None = None,
    ) -> Pause[ContextT, AnswerT]:
        """Create a node that suspends the run to await an answer.

        When the run reaches it, it snapshots and stops, raising
        [`GraphPaused`][openfactcheck.graph.errors.GraphPaused] with the value
        that arrived and ``prompt``. Resume with
        [`Graph.resume_with`][Graph.resume_with]; the answer becomes the node's
        output and flows to its successor. Pausing requires a store and run id
        on the run so the suspended state can be reloaded.

        Args:
            context_type: The type flowing into the pause, recorded for
                build-time edge validation.
            answer_type: The type supplied on resume, recorded for build-time
                edge validation.
            node_id: Identifier for the pause node; must be unique within the graph.
            prompt: A description of what is being asked, surfaced on pause.

        Returns:
            The registered [`Pause`][Pause] node.

        Raises:
            GraphBuildError: If the chosen node id is already in use.
        """
        if self._id_taken(node_id):
            raise GraphBuildError(f"duplicate node id {node_id!r}")
        pause: Pause[ContextT, AnswerT] = Pause(
            id=node_id,
            context_type=context_type,
            answer_type=answer_type,
            prompt=prompt,
        )
        self._pauses[node_id] = pause
        return pause

    def edge_from[EdgeOutputT](
        self,
        source: SourceNode[EdgeOutputT, StateT, DepsT],
    ) -> EdgePathBuilder[EdgeOutputT, StateT, DepsT]:
        """Begin an edge leaving ``source``.

        Args:
            source: The step or start node the edge leaves.

        Returns:
            A builder whose [`to`][EdgePathBuilder.to] names the destination,
            carrying ``source``'s output type so an incompatible destination is
            a type error.
        """
        return EdgePathBuilder(source.id)

    def add(self, *items: Edge | Branch | _InlineJoinEdge) -> None:
        """Register edges and decision branches into the graph being built.

        Args:
            items: Edges from [`edge_from`][GraphBuilder.edge_from], inline-join
                edges from [`collect`][EdgePathBuilder.collect] or
                [`reduce`][EdgePathBuilder.reduce], and branches from a
                [`Decision`][Decision]'s branch methods, in any mix.
        """
        for item in items:
            if isinstance(item, Branch):
                self._branches.append(item)
                self._edges.append(Edge(source_id=item.source_id, dest_id=item.dest_id))
            elif isinstance(item, _InlineJoinEdge):
                self._add_inline_join(item)
            else:
                self._edges.append(item)

    def _add_inline_join(self, item: _InlineJoinEdge) -> None:
        """Expand an inline-join edge into a join node and the edges into and out of it."""
        join_id = f"{item.spec.verb}:{item.source_id}->{item.dest_id}"
        self._add_join(
            item_type=None,
            reducer=self._normalize_reducer(item.spec.reducer),
            initial_factory=item.spec.initial_factory,
            ordered=item.spec.ordered,
            verb=item.spec.verb,
            inline=True,
            node_id=join_id,
        )
        self._edges.append(Edge(source_id=item.source_id, dest_id=join_id))
        self._edges.append(Edge(source_id=join_id, dest_id=item.dest_id))

    def build(self) -> Graph[InputT, OutputT, StateT, DepsT]:
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
        fork_join = self._resolve_fork_joins(edges_by_source)
        spec = GraphSpec(
            steps=self._steps,
            joins=self._joins,
            decisions=self._group_branches(),
            pauses=self._pauses,
            edges_by_source=edges_by_source,
            fork_join=fork_join,
            start_id=START_ID,
            end_id=END_ID,
            state_type=self._state_type,
            input_type=self._input_type,
            output_type=self._output_type,
        )
        return Graph(spec, name=self._name)

    def _group_branches(self) -> dict[str, list[Branch]]:
        """Group each decision's branches in registration order."""
        decisions: dict[str, list[Branch]] = {decision_id: [] for decision_id in self._decisions}
        for branch in self._branches:
            decisions[branch.source_id].append(branch)
        return decisions

    def _index_edges(self) -> dict[str, list[Edge]]:
        """Group edges by source after checking that every endpoint is known."""
        node_ids = {START_ID, END_ID, *self._steps, *self._joins, *self._decisions, *self._pauses}
        edges_by_source: dict[str, list[Edge]] = {}
        for edge in self._edges:
            if edge.source_id not in node_ids:
                raise GraphBuildError(f"edge from unknown node {edge.source_id!r}")
            if edge.dest_id not in node_ids:
                raise GraphBuildError(f"edge to unknown node {edge.dest_id!r}")
            edges_by_source.setdefault(edge.source_id, []).append(edge)
        return edges_by_source

    def _validate_endpoints(self, edges_by_source: dict[str, list[Edge]]) -> None:
        """Check that the start, end, and every work-bearing node are wired in."""
        if START_ID not in edges_by_source:
            raise GraphValidationError("graph has no entry edge from the start node")
        if all(edge.dest_id != END_ID for edge in self._edges):
            raise GraphValidationError("graph has no edge into the end node")
        for node_id in (*self._steps, *self._joins, *self._decisions, *self._pauses):
            if node_id not in edges_by_source:
                raise GraphValidationError(f"node {node_id!r} has no outgoing edge")

    def _validate_reachability(self, edges_by_source: dict[str, list[Edge]]) -> None:
        """Check that every work-bearing node and the end node are reachable from the start."""
        seen: set[str] = set()
        queue = deque([START_ID])
        while queue:
            node_id = queue.popleft()
            for edge in edges_by_source.get(node_id, []):
                if edge.dest_id not in seen:
                    seen.add(edge.dest_id)
                    queue.append(edge.dest_id)
        unreachable = sorted({*self._steps, *self._joins, *self._decisions, *self._pauses} - seen)
        if unreachable:
            raise GraphValidationError(f"nodes are not reachable from the start node: {unreachable}")
        if END_ID not in seen:
            raise GraphValidationError("the end node is not reachable from the start node")

    def _validate_edge_types(self) -> None:
        """Raise if any plain step-to-step edge connects an incompatible output and input.

        Edges touching the start node, end node, or a join are skipped, as those
        carry no captured step type. Map edges are skipped too: their source
        emits a collection whose item type feeds the destination, a relationship
        the static [`map`][EdgePathBuilder.map] check already enforces.

        Raises:
            GraphValidationError: If a known output type does not match the
                known input type of the node it feeds.
        """
        for edge in self._edges:
            if edge.kind is EdgeKind.MAP:
                continue
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

    def _resolve_fork_joins(self, edges_by_source: dict[str, list[Edge]]) -> dict[str, str]:
        """Map each map edge's fork to the join node that collects its branches.

        Args:
            edges_by_source: Outgoing edges grouped by source node id.

        Returns:
            A mapping from each map fork's id to its downstream join id, used at
            run time to fire a join whose collection fanned out to no items.

        Raises:
            GraphValidationError: If a map edge has no downstream join.
        """
        fork_join: dict[str, str] = {}
        for edge in self._edges:
            if edge.kind is not EdgeKind.MAP:
                continue
            join_id = self._downstream_join(edge.dest_id, edges_by_source)
            if join_id is None:
                raise GraphValidationError(
                    f"map edge {edge.source_id!r} -> {edge.dest_id!r} has no downstream join to collect its branches",
                )
            fork_join[f"{edge.source_id}->{edge.dest_id}"] = join_id
        return fork_join

    def _downstream_join(self, start_id: str, edges_by_source: dict[str, list[Edge]]) -> str | None:
        """Return the nearest join reachable from ``start_id``, or ``None`` if there is none."""
        seen: set[str] = set()
        queue = deque([start_id])
        while queue:
            node_id = queue.popleft()
            if node_id in self._joins:
                return node_id
            for edge in edges_by_source.get(node_id, []):
                if edge.dest_id not in seen:
                    seen.add(edge.dest_id)
                    queue.append(edge.dest_id)
        return None

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
                input_type = args[0]
            break
        return input_type, output_type
