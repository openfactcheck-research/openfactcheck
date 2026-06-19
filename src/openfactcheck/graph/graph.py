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
from contextlib import suppress
from dataclasses import dataclass, replace
from time import perf_counter
from typing import TYPE_CHECKING, Generic, Literal, Self, cast

from pydantic import TypeAdapter, ValidationError

from openfactcheck.graph._typevars import DepsT, InputT, OutputT, StateT
from openfactcheck.graph.errors import GraphPaused, GraphPersistenceError, GraphRuntimeError
from openfactcheck.graph.events import NodeEmitted, NodeFailed, NodeFinished, NodeStarted, RunFinished
from openfactcheck.graph.forks import ForkStackItem
from openfactcheck.graph.join import ReducerContext
from openfactcheck.graph.mermaid import (
    _MermaidView,  # pyright: ignore[reportPrivateUsage]
    to_mermaid,
    to_mermaid_image,
)
from openfactcheck.graph.persistence.protocols import JoinSnapshot, PausePoint, RunSnapshot, RunStatus, TaskSnapshot
from openfactcheck.graph.step import EdgeKind, StepContext

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from openfactcheck.graph.decision import Branch
    from openfactcheck.graph.events import GraphEvent, GraphObserver
    from openfactcheck.graph.forks import ForkStack
    from openfactcheck.graph.join import AnyJoin
    from openfactcheck.graph.mermaid import Direction, ImageType
    from openfactcheck.graph.pause import AnyPause
    from openfactcheck.graph.persistence.protocols import StateStore
    from openfactcheck.graph.step import AnyStep, Edge

_UNSET: object = object()
"""Sentinel for "the end node was never reached"."""

_STREAM_END: object = object()
"""Sentinel queued after a streamed run ends, signalling the event stream is exhausted."""

DEFAULT_CONCURRENCY = 8
"""Default cap on the number of step invocations running at once in a single run."""

type ErrorPolicy = Literal["fail_fast", "isolate"]
"""How a run reacts to a step error: abort the whole run, or drop the failed branch and continue."""


@dataclass(frozen=True, slots=True)
class RunOptions:
    """Tuning knobs for a single graph run, separate from its input and state."""

    concurrency: int = DEFAULT_CONCURRENCY
    """Maximum number of step invocations running at once.

    Must be at least one.
    """

    timeout: float | None = None
    """Seconds the whole run may take before it is cancelled, or ``None`` for no limit.

    Must be positive when set.
    """

    on_error: ErrorPolicy = "fail_fast"
    """How a step error is handled: abort the run, or drop the failed branch and continue."""

    on_event: GraphObserver | None = None
    """A callback invoked with each progress event during a run, or ``None`` for none."""

    stream_node_data: bool = False
    """Whether to surface data a node emits via its ``emit`` hook.

    When ``False`` (the default) the stream carries node lifecycle events only and
    a node's ``emit`` calls are discarded. When ``True`` each emitted datum becomes
    a [`NodeEmitted`][openfactcheck.graph.events.NodeEmitted] event tagged with the
    emitting node and its fork branch.
    """

    store: StateStore | None = None
    """A store to snapshot the run to after each task, or ``None`` to not persist."""

    run_id: str | None = None
    """The id snapshots are saved under; required when ``store`` is set."""


@dataclass(frozen=True, slots=True)
class GraphSpec:
    """The immutable, validated definition a run executes against.

    Assembled by [`GraphBuilder.build`][GraphBuilder] and handed to a
    [`Graph`][Graph]; not constructed directly.
    """

    steps: dict[str, AnyStep]
    joins: dict[str, AnyJoin]
    decisions: dict[str, list[Branch]]
    pauses: dict[str, AnyPause]
    edges_by_source: dict[str, list[Edge]]
    fork_join: dict[str, str]
    start_id: str
    end_id: str
    state_type: object | None
    input_type: object | None
    output_type: object | None


@dataclass(frozen=True, slots=True)
class _TaskResult:
    """A finished step's output, or the error it raised, routed back to the run loop."""

    node_id: str
    output: object
    fork_stack: ForkStack
    error: Exception | None
    duration: float
    task_id: int


@dataclass(slots=True)
class _JoinState:
    """Branch outputs accumulated for one firing of one join."""

    downstream_stack: ForkStack
    acc: object
    count: int
    items: list[tuple[int, object]]


@dataclass(frozen=True, slots=True)
class StepResult:
    """One finished task surfaced by a step-by-step run."""

    node_id: str
    """Identifier of the node that ran."""

    output: object
    """The node's output, or ``None`` when it raised."""

    error: Exception | None
    """The error the node raised, or ``None`` on success."""

    fork_stack: ForkStack
    """The fork branch the task belonged to."""


class _GraphRun[StateT, DepsT, OutputT]:
    """Drives one execution of a graph: a concurrent worklist over a task queue.

    The run loop is the single mutator of run state. Workers only execute user
    step functions and report their results back through a queue, so the join
    table and the final value are updated without races.
    """

    def __init__(self, spec: GraphSpec, *, state: StateT, deps: DepsT, options: RunOptions) -> None:
        """Set up an empty run against a graph definition."""
        self._spec = spec
        self._state = state
        self._deps = deps
        self._semaphore = asyncio.Semaphore(options.concurrency)
        self._timeout = options.timeout
        self._on_error = options.on_error
        self._observer = options.on_event
        self._stream_node_data = options.stream_node_data
        self._store = options.store
        self._run_id = options.run_id
        self._results: asyncio.Queue[_TaskResult] = asyncio.Queue()
        self._task_ids: dict[asyncio.Task[None], int] = {}
        self._pending: dict[int, TaskSnapshot] = {}
        self._restored: list[TaskSnapshot] = []
        self._task_seq = 0
        self._active = 0
        self._reducers: dict[tuple[str, str], _JoinState] = {}
        self._finalized: set[tuple[str, str]] = set()
        self._expected: dict[str, int] = {}
        self._loops: dict[tuple[str, str, ForkStack], int] = {}
        self._fork_seq = 0
        self._final: object = _UNSET
        self._paused: PausePoint | None = None

    async def execute(self, inputs: object) -> OutputT:
        """Run to completion and return the value routed into the end node.

        Args:
            inputs: The value handed to the graph's entry edges.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
            TimeoutError: If the whole-run timeout elapses.
        """
        self.seed(inputs)
        return await self._drive()

    async def resume(self) -> OutputT:
        """Re-run the tasks of a loaded snapshot and finish the run.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
            TimeoutError: If the run's timeout elapses.
        """
        for task in self._restored:
            self._spawn(task.node_id, task.value, task.fork_stack)
        return await self._drive()

    async def _drive(self) -> OutputT:
        """Drain the work queue, snapshotting after each task; stop early at a pause."""
        try:
            async with asyncio.timeout(self._timeout):
                while self._paused is None:
                    result = await self.pump()
                    if result is None:
                        break
                    self._pending.pop(result.task_id, None)
                    if result.error is not None:
                        self._emit(NodeFailed(result.node_id, result.error, result.duration, result.fork_stack))
                        if self._on_error == "fail_fast":
                            await self._save(RunStatus.FAILED)
                            raise result.error
                        self.drop_failed(result.fork_stack)
                    else:
                        self._emit(NodeFinished(result.node_id, result.output, result.duration, result.fork_stack))
                        self.route_output(result.node_id, result.output, result.fork_stack)
                    if self._paused is None:
                        await self._save(RunStatus.RUNNING)
        finally:
            await self.cancel_pending()
        if self._paused is not None:
            if self._store is None or self._run_id is None:
                raise GraphRuntimeError(
                    f"run reached pause node {self._paused.node_id!r} but no store and run_id are "
                    "configured; a paused run must be snapshotted to be resumable",
                )
            await self._save(RunStatus.PAUSED, paused=self._paused)
            raise GraphPaused(
                f"run paused at {self._paused.node_id!r}",
                node_id=self._paused.node_id,
                context=self._paused.context,
                prompt=self._paused.prompt,
                run_id=self._run_id,
            )
        output = self.finish()
        await self._save(RunStatus.SUCCEEDED, final_output=output)
        self._emit(RunFinished(output))
        return output

    async def resume_with(self, paused: PausePoint, value: object) -> OutputT:
        """Inject ``value`` as the paused node's output and finish the run.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
            GraphPaused: If the run reaches another pause node.
            TimeoutError: If the run's timeout elapses.
        """
        for task in self._restored:
            self._spawn(task.node_id, task.value, task.fork_stack)
        self.route_output(paused.node_id, value, paused.fork_stack)
        return await self._drive()

    def load(self, snapshot: RunSnapshot) -> None:
        """Restore run state from a snapshot so [`resume`][_GraphRun.resume] can continue it.

        A snapshot loaded from a store carries its values as plain data; this
        restores the run's state, its final output, and each pending node's input
        to the types the graph declares, so resumed steps receive the same typed
        values a fresh run would.
        """
        self._state = cast("StateT", self._coerce(self._spec.state_type, self._state, what="run state"))
        self._reducers = {
            key: _JoinState(state.downstream_stack, state.acc, state.count, list(state.items))
            for key, state in snapshot.reducers.items()
        }
        self._expected = dict(snapshot.expected)
        self._loops = dict(snapshot.loops)
        self._finalized = set(snapshot.finalized)
        self._fork_seq = snapshot.fork_seq
        self._final = (
            self._coerce(self._spec.output_type, snapshot.final, what="final output") if snapshot.has_final else _UNSET
        )
        self._restored = [self._restore_input(task) for task in snapshot.pending]

    def _restore_input(self, task: TaskSnapshot) -> TaskSnapshot:
        """Restore a pending task's input value to its node's declared input type."""
        step = self._spec.steps.get(task.node_id)
        declared = step.input_type if step is not None else None
        return replace(task, value=self._coerce(declared, task.value, what=f"input for node {task.node_id!r}"))

    @staticmethod
    def _coerce(declared: object | None, value: object, *, what: str) -> object:
        """Validate a loaded snapshot value into a declared type, leaving it as-is when untyped.

        Raises:
            GraphPersistenceError: If a value cannot be validated into its declared type.
        """
        if declared is None:
            return value
        adapter: TypeAdapter[object] = TypeAdapter(declared)
        try:
            return adapter.validate_python(value)
        except ValidationError as error:
            raise GraphPersistenceError(f"stored {what} does not match its declared type {declared!r}") from error

    async def _save(
        self, status: RunStatus, *, final_output: object = _UNSET, paused: PausePoint | None = None
    ) -> None:
        """Persist a snapshot of the current run state, if a store is configured."""
        if self._store is None or self._run_id is None:
            return
        await self._store.save(self._snapshot(status, self._run_id, final_output, paused))

    def _snapshot(self, status: RunStatus, run_id: str, final_output: object, paused: PausePoint | None) -> RunSnapshot:
        """Capture the run's resumable state as a snapshot."""
        final = final_output if final_output is not _UNSET else self._final
        return RunSnapshot(
            run_id=run_id,
            status=status,
            pending=tuple(self._pending.values()),
            reducers={
                key: JoinSnapshot(state.downstream_stack, state.acc, state.count, list(state.items))
                for key, state in self._reducers.items()
            },
            expected=dict(self._expected),
            loops=dict(self._loops),
            finalized=frozenset(self._finalized),
            fork_seq=self._fork_seq,
            has_final=final is not _UNSET,
            final=final if final is not _UNSET else None,
            state=self._state,
            paused=paused,
        )

    def _emit(self, event: GraphEvent) -> None:
        """Hand an event to the run's observer, if one is set."""
        if self._observer is not None:
            self._observer(event)

    def seed(self, inputs: object) -> None:
        """Enqueue the tasks reachable from the start node's edges."""
        for edge in self._spec.edges_by_source.get(self._spec.start_id, []):
            self._dispatch(edge, inputs, ())

    async def pump(self) -> _TaskResult | None:
        """Wait for the next finished task and account for it, or ``None`` when the run is idle."""
        if self._active == 0:
            return None
        result = await self._results.get()
        self._active -= 1
        return result

    def route_output(self, node_id: str, output: object, stack: ForkStack) -> None:
        """Enqueue successors for every edge leaving a finished node."""
        for edge in self._spec.edges_by_source.get(node_id, []):
            self._dispatch(edge, output, stack)

    def finish(self) -> OutputT:
        """Return the value routed into the end node, or fail if it was never reached.

        Raises:
            GraphRuntimeError: If the run finished without reaching the end node.
        """
        if self._final is _UNSET:
            raise GraphRuntimeError("run finished without reaching the end node")
        return cast("OutputT", self._final)

    def _dispatch(self, edge: Edge, value: object, stack: ForkStack) -> None:
        """Route one outgoing edge: fan out an iterable, or deliver the whole value."""
        if edge.kind is EdgeKind.MAP:
            self._fan_out(edge, value, stack)
        else:
            self._route(edge.dest_id, value, stack)

    def _route(self, dest_id: str, value: object, stack: ForkStack) -> None:
        """Deliver a value to a node: finish, accumulate, branch, pause, or spawn a step."""
        if dest_id == self._spec.end_id:
            self._final = value
        elif dest_id in self._spec.joins:
            self._accumulate(dest_id, value, stack)
        elif dest_id in self._spec.decisions:
            self._decide(dest_id, value, stack)
        elif dest_id in self._spec.pauses:
            self._pause(dest_id, value, stack)
        else:
            self._spawn(dest_id, value, stack)

    def _pause(self, pause_id: str, value: object, stack: ForkStack) -> None:
        """Mark the run as suspended at a pause node, to stop after the current task."""
        prompt = self._spec.pauses[pause_id].prompt
        self._paused = PausePoint(node_id=pause_id, context=value, fork_stack=stack, prompt=prompt)

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
        stopped = False
        if join.ordered:
            state.items.append((top.branch_index, value))
        else:
            ctx: ReducerContext[StateT, DepsT] = ReducerContext(state=self._state, deps=self._deps)
            state.acc = join.reducer(ctx, state.acc, value)
            state.count += 1
            stopped = ctx.stopped
        self._maybe_complete(join_id, top.fork_run_id, force=stopped)
        if stopped:
            self._cancel_fork_run(top.fork_run_id)

    def _maybe_complete(self, join_id: str, fork_run_id: str, *, force: bool = False) -> None:
        """Fire a join once it has every expected branch, or when stopped early."""
        key = (join_id, fork_run_id)
        if key in self._finalized:
            return
        state = self._reducers.get(key)
        if state is None:
            return
        join = self._spec.joins[join_id]
        count = len(state.items) if join.ordered else state.count
        if force or count >= self._expected.get(fork_run_id, count):
            acc = self._fold_ordered(join, state) if join.ordered else state.acc
            self._finalize_and_fire(join_id, key, acc, state.downstream_stack)

    def drop_failed(self, stack: ForkStack) -> None:
        """Isolate a failed branch: drop it and let its downstream join fire with the survivors."""
        if not stack:
            return
        top = stack[-1]
        join_id = self._spec.fork_join.get(top.fork_id)
        if join_id is None:
            return
        key = (join_id, top.fork_run_id)
        if key in self._finalized:
            return
        self._expected[top.fork_run_id] = self._expected.get(top.fork_run_id, 0) - 1
        if self._reducers.get(key) is None:
            if self._expected[top.fork_run_id] <= 0:
                self._finalized.add(key)
                self._fire(join_id, self._spec.joins[join_id].initial_factory(), stack[:-1])
            return
        self._maybe_complete(join_id, top.fork_run_id)

    def _cancel_fork_run(self, fork_run_id: str) -> None:
        """Cancel any still-running tasks belonging to a fork run that has finished early."""
        for task, task_id in list(self._task_ids.items()):
            snapshot = self._pending.get(task_id)
            if snapshot is None or task.done():
                continue
            if any(frame.fork_run_id == fork_run_id for frame in snapshot.fork_stack):
                task.cancel()
                self._active -= 1
                self._task_ids.pop(task, None)
                self._pending.pop(task_id, None)

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
        """Schedule a step to run, tracking it as in-flight and pending a snapshot."""
        self._emit(NodeStarted(node_id, stack))
        self._task_seq += 1
        task_id = self._task_seq
        self._pending[task_id] = TaskSnapshot(node_id, value, stack)
        self._active += 1
        task = asyncio.create_task(self._worker(node_id, value, stack, task_id))
        self._task_ids[task] = task_id
        task.add_done_callback(self._forget_task)

    def _forget_task(self, task: asyncio.Task[None]) -> None:
        """Drop a finished task from the in-flight set."""
        self._task_ids.pop(task, None)

    async def _worker(self, node_id: str, value: object, stack: ForkStack, task_id: int) -> None:
        """Run one step, with retries and timeout, and report its result."""
        step = self._spec.steps[node_id]
        ctx: StepContext[object, StateT, DepsT] = StepContext(inputs=value, state=self._state, deps=self._deps)
        if self._stream_node_data:

            def emit(data: object) -> None:
                self._emit(NodeEmitted(node_id, data, stack))

            ctx = replace(ctx, emit=emit)
        started = perf_counter()
        try:
            output = await self._run_step(step, ctx)
        except Exception as error:  # noqa: BLE001 - surfaced to the run loop for ordered handling.
            await self._results.put(_TaskResult(node_id, None, stack, error, perf_counter() - started, task_id))
            return
        await self._results.put(_TaskResult(node_id, output, stack, None, perf_counter() - started, task_id))

    async def _run_step(self, step: AnyStep, ctx: StepContext[object, StateT, DepsT]) -> object:
        """Invoke a step under the concurrency limit, retrying on failure with backoff.

        Raises:
            Exception: The step's error, re-raised once its retries are exhausted.
            TimeoutError: If an attempt exceeds the step's timeout and no retries remain.
        """
        attempt = 0
        while True:
            try:
                async with self._semaphore, asyncio.timeout(step.timeout):
                    return await step.call(ctx)
            except Exception:
                if attempt >= step.retries:
                    raise
                attempt += 1
            await asyncio.sleep(step.retry_backoff * 2 ** (attempt - 1))

    def _next_fork_run_id(self) -> str:
        """Mint a fresh identifier for one firing of a fork."""
        self._fork_seq += 1
        return f"r{self._fork_seq}"

    async def cancel_pending(self) -> None:
        """Cancel and drain any still-running step tasks."""
        pending = list(self._task_ids)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


class GraphStepper[OutputT, StateT, DepsT]:
    """A handle that advances a run one task at a time.

    Obtained from [`Graph.stepper`][Graph.stepper] and used as an async context
    manager. Call [`advance`][GraphStepper.advance] to run the next task and get
    a [`StepResult`][StepResult] describing it, looping until ``advance`` returns
    ``None``. A failed task can be resumed with [`recover`][GraphStepper.recover];
    once the run is complete, read [`output`][GraphStepper.output].

    Example:
        ```python
        async with graph.stepper(inputs, state=None, deps=None) as run:
            while (step := await run.advance()) is not None:
                if step.error is not None:
                    run.recover(step, fallback)
        result = run.output
        ```
    """

    def __init__(self, run: _GraphRun[StateT, DepsT, OutputT], inputs: object) -> None:
        """Wrap an executor and the input that seeds it; construct via [`Graph.stepper`][Graph.stepper]."""
        self._run = run
        self._inputs = inputs

    async def __aenter__(self) -> Self:
        """Seed the run from the graph input and return the handle."""
        self._run.seed(self._inputs)
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Cancel any tasks still running when the block exits."""
        await self._run.cancel_pending()

    async def advance(self) -> StepResult | None:
        """Run the next task, dispatch its successors on success, and report it.

        Returns:
            The finished task's [`StepResult`][StepResult], or ``None`` once no
            tasks remain. A result with an ``error`` has not been routed onward:
            call [`recover`][GraphStepper.recover] to resume it with a fallback,
            or [`drop`][GraphStepper.drop] to drop its branch.
        """
        result = await self._run.pump()
        if result is None:
            return None
        if result.error is None:
            self._run.route_output(result.node_id, result.output, result.fork_stack)
        return StepResult(
            node_id=result.node_id,
            output=result.output,
            error=result.error,
            fork_stack=result.fork_stack,
        )

    def recover(self, step: StepResult, output: object) -> None:
        """Resume a failed task by routing ``output`` as if its node had returned it.

        Args:
            step: The failed [`StepResult`][StepResult] from
                [`advance`][GraphStepper.advance].
            output: The value to route onward in place of the missing output.
        """
        self._run.route_output(step.node_id, output, step.fork_stack)

    def drop(self, step: StepResult) -> None:
        """Drop a failed step's branch so its downstream join can fire without it.

        The counterpart to [`recover`][GraphStepper.recover]: where ``recover``
        supplies a replacement value, ``drop`` abandons the branch and lets any
        join awaiting it complete with the branches that did arrive.

        Args:
            step: The failed [`StepResult`][StepResult] from
                [`advance`][GraphStepper.advance].
        """
        self._run.drop_failed(step.fork_stack)

    @property
    def output(self) -> OutputT:
        """The value routed into the end node, valid once the run is complete.

        Raises:
            GraphRuntimeError: If the end node was never reached.
        """
        return self._run.finish()


class Graph(Generic[InputT, OutputT, StateT, DepsT]):
    """An executable graph of typed nodes.

    Assembled by [`GraphBuilder.build`][GraphBuilder] rather than constructed
    directly. Run it with [`run`][Graph.run] or its async peer
    [`arun`][Graph.arun], or drive it one task at a time with
    [`stepper`][Graph.stepper]. The type parameters, in order, are:

    1. ``InputT``: the value the graph accepts.
    2. ``OutputT``: the value the graph returns.
    3. ``StateT``: run-scoped mutable state shared across every node. Optional;
       defaults to ``None`` (no shared state).
    4. ``DepsT``: read-only dependencies injected into every node (clients,
       configuration). Optional; defaults to ``None`` (no deps).

    Pass the matching ``state`` and ``deps`` when running; they flow unchanged
    into every [`StepContext`][StepContext].

    Example:
        ```python
        # str in, a dict out, no shared state, a Deps bag of clients.
        graph = builder.build()  # Graph[str, dict[str, int], None, Deps]
        result = graph.run("hello", state=None, deps=Deps(...))
        ```
    """

    def __init__(self, spec: GraphSpec, *, name: str) -> None:
        """Record the validated definition of a built graph.

        Args:
            spec: The validated nodes, edges, and routing from the builder.
            name: Human-readable name for diagrams and logs.
        """
        self._spec = spec
        self.name = name

    def to_mermaid(
        self,
        *,
        direction: Direction = "TD",
        title: str | None = None,
        highlight: Iterable[str] | None = None,
        show_types: bool = False,
    ) -> str:
        """Render this graph as Mermaid flowchart source.

        Args:
            direction: Layout direction of the flowchart.
            title: An optional title shown above the diagram.
            highlight: Node ids to draw with a highlight style.
            show_types: Label each edge with the type of data it carries, read
                from the source node's declared output type.

        Returns:
            Mermaid flowchart source as a string.
        """
        return to_mermaid(self._spec, direction=direction, title=title, highlight=highlight, show_types=show_types)

    def to_mermaid_image(
        self, *, base_url: str = "https://mermaid.ink", image_type: ImageType = "png", timeout: float = 30.0
    ) -> bytes:
        """Render this graph as an image through a Mermaid server.

        Args:
            base_url: Base URL of the Mermaid rendering server; point it at a
                self-hosted server to render offline or to handle a large diagram.
            image_type: Image format to request.
            timeout: Seconds to wait for the server before giving up.

        Returns:
            The rendered image's raw bytes.

        Raises:
            GraphRenderError: If the server cannot be reached or returns an error.
        """
        return to_mermaid_image(self.to_mermaid(), base_url=base_url, image_type=image_type, timeout=timeout)

    def to_mermaid_view(self, *, base_url: str = "https://mermaid.ink", timeout: float = 30.0) -> _MermaidView:
        """Render this graph as a PNG that displays inline in a notebook.

        Returns an object a notebook renders as the diagram image; elsewhere,
        reach for [`to_mermaid_image`][Graph.to_mermaid_image] to get the bytes directly.

        Args:
            base_url: Base URL of the Mermaid rendering server; point it at a
                self-hosted server to render offline or to handle a large diagram.
            timeout: Seconds to wait for the server before giving up.

        Returns:
            A display wrapper a notebook shows as the rendered diagram.

        Raises:
            GraphRenderError: If the server cannot be reached or returns an error.
        """
        return _MermaidView(self.to_mermaid_image(base_url=base_url, timeout=timeout))

    def __str__(self) -> str:
        """Return this graph as Mermaid flowchart source."""
        return to_mermaid(self._spec)

    @staticmethod
    def _validated(options: RunOptions | None) -> RunOptions:
        """Resolve run options and check them, defaulting when none are given.

        Raises:
            ValueError: If concurrency is less than one, or a store is set
                without a run id.
        """
        resolved = options if options is not None else RunOptions()
        if resolved.concurrency < 1:
            raise ValueError(f"concurrency must be at least 1, got {resolved.concurrency}")
        if resolved.store is not None and resolved.run_id is None:
            raise ValueError("run_id is required when a store is set")
        return resolved

    async def arun(self, inputs: InputT, *, state: StateT, deps: DepsT, options: RunOptions | None = None) -> OutputT:
        """Run the graph to completion and return its terminal output.

        Args:
            inputs: The value handed to the first node.
            state: Run-scoped state shared across nodes.
            deps: Run-scoped dependencies injected into nodes.
            options: Concurrency, timeout, and error-handling knobs for the run;
                defaults to [`RunOptions`][RunOptions]'s own defaults.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
            TimeoutError: If the run's timeout elapses.
            ValueError: If the configured concurrency is less than one.
        """
        resolved = self._validated(options)
        run: _GraphRun[StateT, DepsT, OutputT] = _GraphRun(self._spec, state=state, deps=deps, options=resolved)
        return await run.execute(inputs)

    def run(self, inputs: InputT, *, state: StateT, deps: DepsT, options: RunOptions | None = None) -> OutputT:
        """Run the graph to completion synchronously.

        A blocking wrapper over [`arun`][Graph.arun] for scripts and notebooks.
        Call ``arun`` directly from inside a running event loop.

        Args:
            inputs: The value handed to the first node.
            state: Run-scoped state shared across nodes.
            deps: Run-scoped dependencies injected into nodes.
            options: Concurrency, timeout, and error-handling knobs for the run;
                defaults to [`RunOptions`][RunOptions]'s own defaults.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
            TimeoutError: If the run's timeout elapses.
            ValueError: If the configured concurrency is less than one.
        """
        return asyncio.run(self.arun(inputs, state=state, deps=deps, options=options))

    async def astream(
        self,
        inputs: InputT,
        *,
        state: StateT,
        deps: DepsT,
        options: RunOptions | None = None,
    ) -> AsyncIterator[GraphEvent]:
        """Run the graph and yield progress events as they happen.

        Yields a [`NodeStarted`][openfactcheck.graph.events.NodeStarted] and a
        [`NodeFinished`][openfactcheck.graph.events.NodeFinished] (or
        [`NodeFailed`][openfactcheck.graph.events.NodeFailed]) per task, then a
        final [`RunFinished`][openfactcheck.graph.events.RunFinished]. When
        ``stream_node_data`` is set, a node's ``emit`` calls additionally appear as
        [`NodeEmitted`][openfactcheck.graph.events.NodeEmitted] events between its
        start and finish. Any ``on_event`` set in ``options`` is ignored; the
        stream is the observer.

        Args:
            inputs: The value handed to the first node.
            state: Run-scoped state shared across nodes.
            deps: Run-scoped dependencies injected into nodes.
            options: Concurrency, timeout, and error-handling knobs for the run.

        Yields:
            Each [`GraphEvent`][openfactcheck.graph.events.GraphEvent] in turn.

        Raises:
            GraphRuntimeError: If the run finishes without reaching the end node.
            TimeoutError: If the run's timeout elapses.
            ValueError: If the configured concurrency is less than one.
        """
        resolved = self._validated(options)
        events: asyncio.Queue[GraphEvent | object] = asyncio.Queue()
        streaming = replace(resolved, on_event=events.put_nowait)
        run: _GraphRun[StateT, DepsT, OutputT] = _GraphRun(self._spec, state=state, deps=deps, options=streaming)
        drive = asyncio.create_task(self._drain_run(run, inputs, events))
        try:
            while True:
                event = await events.get()
                if event is _STREAM_END:
                    break
                yield cast("GraphEvent", event)
            await drive
        finally:
            if not drive.done():
                drive.cancel()
                with suppress(asyncio.CancelledError):
                    await drive

    @staticmethod
    async def _drain_run(
        run: _GraphRun[StateT, DepsT, OutputT],
        inputs: object,
        events: asyncio.Queue[GraphEvent | object],
    ) -> None:
        """Execute a run, then mark its event stream complete."""
        try:
            await run.execute(inputs)
        finally:
            events.put_nowait(_STREAM_END)

    def stepper(
        self,
        inputs: InputT,
        *,
        state: StateT,
        deps: DepsT,
        options: RunOptions | None = None,
    ) -> GraphStepper[OutputT, StateT, DepsT]:
        """Drive the graph one task at a time for inspection or recovery.

        Returns an async-context-manager handle; see
        [`GraphStepper`][GraphStepper] for the loop.

        Args:
            inputs: The value handed to the first node.
            state: Run-scoped state shared across nodes.
            deps: Run-scoped dependencies injected into nodes.
            options: Concurrency, timeout, and error-handling knobs; note the
                whole-run timeout and ``on_error`` policy do not apply while
                stepping, since the caller drives and handles each task.

        Returns:
            A [`GraphStepper`][GraphStepper] over a fresh run.

        Raises:
            ValueError: If the configured concurrency is less than one.
        """
        resolved = self._validated(options)
        run: _GraphRun[StateT, DepsT, OutputT] = _GraphRun(self._spec, state=state, deps=deps, options=resolved)
        return GraphStepper(run, inputs)

    async def aresume(
        self, run_id: str, *, store: StateStore, deps: DepsT, options: RunOptions | None = None
    ) -> OutputT:
        """Resume a snapshotted run from its latest snapshot and finish it.

        Loads the snapshot, restores the run's state, and re-runs the tasks that
        were still pending. Pending tasks run again, so steps should be safe to
        re-run. The run's state and each pending node's input are restored to the
        types the graph declares, so resumed steps receive the same typed values
        a fresh run would. Dependencies are not persisted and are supplied here;
        the run continues to snapshot under the same id and store.

        Args:
            run_id: The id the run was snapshotted under.
            store: The store holding the run's snapshots.
            deps: Run-scoped dependencies injected into nodes.
            options: Concurrency, timeout, and error-handling knobs for the
                resumed run.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If no snapshot exists for ``run_id`` or the run
                finishes without reaching the end node.
            ValueError: If the configured concurrency is less than one.
        """
        snapshot = await store.load(run_id)
        if snapshot is None:
            raise GraphRuntimeError(f"no snapshot found for run {run_id!r}")
        resolved = replace(self._validated(options), store=store, run_id=run_id)
        run: _GraphRun[StateT, DepsT, OutputT] = _GraphRun(
            self._spec,
            state=cast("StateT", snapshot.state),
            deps=deps,
            options=resolved,
        )
        run.load(snapshot)
        return await run.resume()

    def resume(self, run_id: str, *, store: StateStore, deps: DepsT, options: RunOptions | None = None) -> OutputT:
        """Resume a snapshotted run synchronously.

        A blocking wrapper over [`aresume`][Graph.aresume] for scripts and notebooks.

        Args:
            run_id: The id the run was snapshotted under.
            store: The store holding the run's snapshots.
            deps: Run-scoped dependencies injected into nodes.
            options: Concurrency, timeout, and error-handling knobs.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If no snapshot exists for ``run_id`` or the run
                finishes without reaching the end node.
            ValueError: If the configured concurrency is less than one.
        """
        return asyncio.run(self.aresume(run_id, store=store, deps=deps, options=options))

    async def aresume_with(
        self,
        run_id: str,
        *,
        store: StateStore,
        deps: DepsT,
        value: object,
        options: RunOptions | None = None,
    ) -> OutputT:
        """Resume a paused run, injecting ``value`` as the pause node's output.

        Args:
            run_id: The id the paused run was snapshotted under.
            store: The store holding the run's snapshots.
            deps: Run-scoped dependencies injected into nodes.
            value: The answer to inject; becomes the pause node's output.
            options: Concurrency, timeout, and error-handling knobs.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If no snapshot exists for ``run_id``, the snapshot
                is not paused, or the run finishes without reaching the end node.
            GraphPaused: If the run reaches another pause node.
            ValueError: If the configured concurrency is less than one.
        """
        snapshot = await store.load(run_id)
        if snapshot is None:
            raise GraphRuntimeError(f"no snapshot found for run {run_id!r}")
        if snapshot.paused is None:
            raise GraphRuntimeError(f"run {run_id!r} is not paused")
        resolved = replace(self._validated(options), store=store, run_id=run_id)
        run: _GraphRun[StateT, DepsT, OutputT] = _GraphRun(
            self._spec,
            state=cast("StateT", snapshot.state),
            deps=deps,
            options=resolved,
        )
        run.load(snapshot)
        return await run.resume_with(snapshot.paused, value)

    def resume_with(
        self,
        run_id: str,
        *,
        store: StateStore,
        deps: DepsT,
        value: object,
        options: RunOptions | None = None,
    ) -> OutputT:
        """Resume a paused run synchronously, injecting ``value`` as the pause node's output.

        A blocking wrapper over [`aresume_with`][Graph.aresume_with].

        Args:
            run_id: The id the paused run was snapshotted under.
            store: The store holding the run's snapshots.
            deps: Run-scoped dependencies injected into nodes.
            value: The answer to inject; becomes the pause node's output.
            options: Concurrency, timeout, and error-handling knobs.

        Returns:
            The value routed into the end node.

        Raises:
            GraphRuntimeError: If no snapshot exists for ``run_id``, the snapshot
                is not paused, or the run finishes without reaching the end node.
            GraphPaused: If the run reaches another pause node.
            ValueError: If the configured concurrency is less than one.
        """
        return asyncio.run(self.aresume_with(run_id, store=store, deps=deps, value=value, options=options))
