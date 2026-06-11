"""The built graph and its concurrent executor.

A [`Graph`][Graph] is the runnable artifact produced by
[`GraphBuilder.build`][GraphBuilder]. A run drains a work queue of tasks, each
carrying a node, its input value, and a fork stack identifying the branch it
belongs to. A node runs and its outgoing edges enqueue successors: a plain edge
hands the whole output to one successor; a map edge fans an iterable out to one
branch per item, each running concurrently up to a bounded limit; a join
collects a fork's branch outputs into a list and forwards it once every branch
has arrived. The value routed into the end node is the run's result.

The async [`arun`][Graph.arun] is the native entry point; the sync
[`run`][Graph.run] wraps it for scripts and notebooks.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from openfactcheck.graph.errors import GraphRuntimeError
from openfactcheck.graph.forks import ForkStackItem
from openfactcheck.graph.join import ReducerContext
from openfactcheck.graph.step import EdgeKind, StepContext

if TYPE_CHECKING:
    from openfactcheck.graph.decision import Branch
    from openfactcheck.graph.forks import ForkStack
    from openfactcheck.graph.join import AnyJoin
    from openfactcheck.graph.step import AnyStep, Edge

_UNSET: object = object()
"""Sentinel for "the end node was never reached"."""

DEFAULT_CONCURRENCY = 8
"""Default cap on the number of step invocations running at once in a single run."""


@dataclass(frozen=True, slots=True)
class GraphSpec:
    """The immutable, validated definition a run executes against.

    Assembled by [`GraphBuilder.build`][GraphBuilder] and handed to a
    [`Graph`][Graph]; not constructed directly.
    """

    steps: dict[str, AnyStep]
    joins: dict[str, AnyJoin]
    decisions: dict[str, list[Branch]]
    edges_by_source: dict[str, list[Edge]]
    fork_join: dict[str, str]
    start_id: str
    end_id: str


@dataclass(frozen=True, slots=True)
class _TaskResult:
    """A finished step's output, or the error it raised, routed back to the run loop."""

    node_id: str
    output: object
    fork_stack: ForkStack
    error: Exception | None


@dataclass(slots=True)
class _JoinState:
    """Branch outputs accumulated for one firing of one join."""

    downstream_stack: ForkStack
    acc: object
    count: int
    items: list[tuple[int, object]]


class _GraphRun[StateT, DepsT, OutputT]:
    """Drives one execution of a graph: a concurrent worklist over a task queue.

    The run loop is the single mutator of run state. Workers only execute user
    step functions and report their results back through a queue, so the join
    table and the final value are updated without races.
    """

    def __init__(self, spec: GraphSpec, *, state: StateT, deps: DepsT, concurrency: int) -> None:
        """Set up an empty run against a graph definition."""
        self._spec = spec
        self._state = state
        self._deps = deps
        self._semaphore = asyncio.Semaphore(concurrency)
        self._results: asyncio.Queue[_TaskResult] = asyncio.Queue()
        self._tasks: set[asyncio.Task[None]] = set()
        self._active = 0
        self._reducers: dict[tuple[str, str], _JoinState] = {}
        self._finalized: set[tuple[str, str]] = set()
        self._expected: dict[str, int] = {}
        self._loops: dict[tuple[str, str, ForkStack], int] = {}
        self._fork_seq = 0
        self._final: object = _UNSET

    async def execute(self, inputs: object) -> OutputT:
        """Run to completion and return the value routed into the end node.

        Args:
            inputs: The value handed to the graph's entry edges.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
        """
        for edge in self._spec.edges_by_source.get(self._spec.start_id, []):
            self._dispatch(edge, inputs, ())
        try:
            while self._active > 0:
                result = await self._results.get()
                self._active -= 1
                if result.error is not None:
                    raise result.error
                self._advance(result.node_id, result.output, result.fork_stack)
        finally:
            await self._cancel_pending()
        if self._final is _UNSET:
            raise GraphRuntimeError("run finished without reaching the end node")
        return cast("OutputT", self._final)

    def _advance(self, node_id: str, output: object, stack: ForkStack) -> None:
        """Enqueue successors for every edge leaving a finished node."""
        for edge in self._spec.edges_by_source.get(node_id, []):
            self._dispatch(edge, output, stack)

    def _dispatch(self, edge: Edge, value: object, stack: ForkStack) -> None:
        """Route one outgoing edge: fan out an iterable, or deliver the whole value."""
        if edge.kind is EdgeKind.MAP:
            self._fan_out(edge, value, stack)
        else:
            self._route(edge.dest_id, value, stack)

    def _route(self, dest_id: str, value: object, stack: ForkStack) -> None:
        """Deliver a value to a node: finish, accumulate at a join, branch, or spawn a step."""
        if dest_id == self._spec.end_id:
            self._final = value
        elif dest_id in self._spec.joins:
            self._accumulate(dest_id, value, stack)
        elif dest_id in self._spec.decisions:
            self._decide(dest_id, value, stack)
        else:
            self._spawn(dest_id, value, stack)

    def _decide(self, decision_id: str, value: object, stack: ForkStack) -> None:
        """Route a value to the first matching branch of a decision, or its default."""
        default: Branch | None = None
        for branch in self._spec.decisions[decision_id]:
            if branch.condition is None:
                default = branch
            elif branch.condition(value):
                self._take_branch(branch, value, stack)
                return
        if default is not None:
            self._take_branch(default, value, stack)
            return
        raise GraphRuntimeError(
            f"decision {decision_id!r} had no matching branch for a value of type {type(value).__name__}",
        )

    def _take_branch(self, branch: Branch, value: object, stack: ForkStack) -> None:
        """Route a chosen branch, enforcing its loop bound when it has one."""
        if branch.max_iterations is not None:
            key = (branch.source_id, branch.dest_id, stack)
            count = self._loops.get(key, 0) + 1
            self._loops[key] = count
            if count > branch.max_iterations:
                raise GraphRuntimeError(
                    f"loop {branch.source_id!r} -> {branch.dest_id!r} exceeded its bound of {branch.max_iterations}",
                )
        self._route(branch.dest_id, value, stack)

    def _fan_out(self, edge: Edge, value: object, stack: ForkStack) -> None:
        """Fan an iterable output out to one branch per item, recording the branch count."""
        if not isinstance(value, Iterable):
            raise GraphRuntimeError(
                f"map edge {edge.source_id!r} -> {edge.dest_id!r} expected an iterable output, "
                f"got {type(value).__name__}",
            )
        fork_id = f"{edge.source_id}->{edge.dest_id}"
        fork_run_id = self._next_fork_run_id()
        items: list[object] = list(cast("Iterable[object]", value))
        self._expected[fork_run_id] = len(items)
        if not items:
            join_id = self._spec.fork_join[fork_id]
            self._finalized.add((join_id, fork_run_id))
            self._fire(join_id, self._spec.joins[join_id].initial_factory(), stack)
            return
        for index, item in enumerate(items):
            self._spawn(edge.dest_id, item, (*stack, ForkStackItem(fork_id, fork_run_id, index)))

    def _accumulate(self, join_id: str, value: object, stack: ForkStack) -> None:
        """Fold one branch's value into a join; fire it when complete or stopped early."""
        if not stack:
            raise GraphRuntimeError(f"join {join_id!r} received a value that is not inside any fork")
        top = stack[-1]
        key = (join_id, top.fork_run_id)
        if key in self._finalized:
            return
        join = self._spec.joins[join_id]
        state = self._reducers.get(key)
        if state is None:
            state = self._reducers[key] = _JoinState(
                downstream_stack=stack[:-1],
                acc=join.initial_factory(),
                count=0,
                items=[],
            )
        expected = self._expected.get(top.fork_run_id)
        if join.ordered:
            state.items.append((top.branch_index, value))
            if len(state.items) == expected:
                self._finalize_and_fire(join_id, key, self._fold_ordered(join, state), state.downstream_stack)
            return
        ctx: ReducerContext[StateT, DepsT] = ReducerContext(state=self._state, deps=self._deps)
        state.acc = join.reducer(ctx, state.acc, value)
        state.count += 1
        if ctx.stopped or state.count == expected:
            self._finalize_and_fire(join_id, key, state.acc, state.downstream_stack)

    def _fold_ordered(self, join: AnyJoin, state: _JoinState) -> object:
        """Fold a join's branch values in source order, starting from its seeded accumulator."""
        ctx: ReducerContext[StateT, DepsT] = ReducerContext(state=self._state, deps=self._deps)
        acc = state.acc
        for _, value in sorted(state.items, key=lambda pair: pair[0]):
            acc = join.reducer(ctx, acc, value)
        return acc

    def _finalize_and_fire(self, join_id: str, key: tuple[str, str], acc: object, stack: ForkStack) -> None:
        """Mark a join firing complete and forward its folded value to its successors."""
        self._reducers.pop(key, None)
        self._finalized.add(key)
        self._fire(join_id, acc, stack)

    def _fire(self, join_id: str, value: object, stack: ForkStack) -> None:
        """Forward a completed join's folded value to its successors."""
        for edge in self._spec.edges_by_source.get(join_id, []):
            self._dispatch(edge, value, stack)

    def _spawn(self, node_id: str, value: object, stack: ForkStack) -> None:
        """Schedule a step to run, tracking it as in-flight."""
        self._active += 1
        task = asyncio.create_task(self._worker(node_id, value, stack))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _worker(self, node_id: str, value: object, stack: ForkStack) -> None:
        """Run one step under the concurrency limit and report its result."""
        step = self._spec.steps[node_id]
        ctx: StepContext[StateT, DepsT, object] = StepContext(inputs=value, state=self._state, deps=self._deps)
        try:
            async with self._semaphore:
                output = await step.call(ctx)
        except Exception as error:  # noqa: BLE001 - surfaced to the run loop for ordered raising and cancellation.
            await self._results.put(_TaskResult(node_id, None, stack, error))
            return
        await self._results.put(_TaskResult(node_id, output, stack, None))

    def _next_fork_run_id(self) -> str:
        """Mint a fresh identifier for one firing of a fork."""
        self._fork_seq += 1
        return f"r{self._fork_seq}"

    async def _cancel_pending(self) -> None:
        """Cancel and drain any still-running step tasks."""
        pending = list(self._tasks)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


class Graph[StateT, DepsT, InputT, OutputT]:
    """An executable graph of typed nodes.

    Assembled by [`GraphBuilder.build`][GraphBuilder]; construct it through the
    builder rather than directly. Run it with [`run`][Graph.run] or its async
    peer [`arun`][Graph.arun].
    """

    def __init__(self, spec: GraphSpec, *, name: str) -> None:
        """Record the validated definition of a built graph.

        Args:
            spec: The validated nodes, edges, and routing from the builder.
            name: Human-readable name for diagrams and logs.
        """
        self._spec = spec
        self.name = name

    async def arun(
        self,
        inputs: InputT,
        *,
        state: StateT,
        deps: DepsT,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> OutputT:
        """Run the graph to completion and return its terminal output.

        Args:
            inputs: The value handed to the first node.
            state: Run-scoped state shared across nodes.
            deps: Run-scoped dependencies injected into nodes.
            concurrency: Maximum number of step invocations running at once.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
            ValueError: If ``concurrency`` is less than one.
        """
        if concurrency < 1:
            raise ValueError(f"concurrency must be at least 1, got {concurrency}")
        run: _GraphRun[StateT, DepsT, OutputT] = _GraphRun(
            self._spec,
            state=state,
            deps=deps,
            concurrency=concurrency,
        )
        return await run.execute(inputs)

    def run(
        self,
        inputs: InputT,
        *,
        state: StateT,
        deps: DepsT,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> OutputT:
        """Run the graph to completion synchronously.

        A blocking wrapper over [`arun`][Graph.arun] for scripts and notebooks.
        Call ``arun`` directly from inside a running event loop.

        Args:
            inputs: The value handed to the first node.
            state: Run-scoped state shared across nodes.
            deps: Run-scoped dependencies injected into nodes.
            concurrency: Maximum number of step invocations running at once.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
            ValueError: If ``concurrency`` is less than one.
        """
        return asyncio.run(self.arun(inputs, state=state, deps=deps, concurrency=concurrency))
