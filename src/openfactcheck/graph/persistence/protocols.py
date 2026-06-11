"""The snapshot model and the pluggable store interface for run persistence.

A [`RunSnapshot`][RunSnapshot] is a plain-data picture of a run at a task
boundary: the tasks still to run, the join accumulators in progress, the loop
counters, and the shared state, plus the terminal output once it exists. A
[`StateStore`][StateStore] saves and loads these snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from openfactcheck.graph.forks import ForkStack


class RunStatus(StrEnum):
    """Where a run is in its lifecycle."""

    CREATED = "created"
    """Set up but not yet started."""

    RUNNING = "running"
    """Executing tasks."""

    PAUSED = "paused"
    """Suspended awaiting external input."""

    SUCCEEDED = "succeeded"
    """Finished and produced its terminal output."""

    FAILED = "failed"
    """Aborted by an error."""


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    """A task that still needs to run when a run is resumed."""

    node_id: str
    """Identifier of the node to run."""

    value: object
    """The input value the node receives."""

    fork_stack: ForkStack
    """The fork branch the task belongs to."""


@dataclass(frozen=True, slots=True)
class JoinSnapshot:
    """One join's accumulation in progress at snapshot time."""

    downstream_stack: ForkStack
    """The fork stack the join emits with once it fires."""

    acc: object
    """The accumulator so far, for an unordered reducer."""

    count: int
    """How many branches have arrived, for an unordered reducer."""

    items: list[tuple[int, object]]
    """The collected ``(branch index, value)`` pairs, for an ordered collect."""


@dataclass(frozen=True, slots=True)
class PausePoint:
    """Where a run suspended at a pause node, and what it is asking for."""

    node_id: str
    """Identifier of the pause node the run stopped at."""

    context: object
    """The value that arrived at the pause node, shown to whoever answers."""

    fork_stack: ForkStack
    """The fork branch the paused value belongs to."""

    prompt: str | None
    """A human-readable description of what is being asked, if the node set one."""


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    """A run's resumable state captured at a task boundary."""

    run_id: str
    """Identifier the snapshot is stored and resumed under."""

    status: RunStatus
    """The run's lifecycle status when the snapshot was taken."""

    pending: tuple[TaskSnapshot, ...]
    """Tasks spawned but not yet processed; re-run on resume."""

    reducers: dict[tuple[str, str], JoinSnapshot]
    """Join accumulations in progress, keyed by ``(join id, fork run id)``."""

    expected: dict[str, int]
    """Branch counts per fork run, keyed by fork run id."""

    loops: dict[tuple[str, str, ForkStack], int]
    """Loop-branch traversal counts, keyed by ``(source, destination, fork stack)``."""

    finalized: frozenset[tuple[str, str]]
    """Joins already fired, keyed by ``(join id, fork run id)``."""

    fork_seq: int
    """The fork-run id counter, so resumed forks keep minting distinct ids."""

    has_final: bool
    """Whether the end node was reached and ``final`` holds the output."""

    final: object
    """The terminal output when ``has_final`` is true, otherwise ``None``."""

    state: object
    """The run-scoped state shared across nodes."""

    paused: PausePoint | None = None
    """Where the run is suspended when its status is paused, otherwise ``None``."""


@runtime_checkable
class StateStore(Protocol):
    """Saves and loads run snapshots so a run can be resumed."""

    async def save(self, snapshot: RunSnapshot) -> None:
        """Append ``snapshot`` to its run's history."""
        ...

    async def load(self, run_id: str) -> RunSnapshot | None:
        """Return the latest snapshot for ``run_id``, or ``None`` if there is none."""
        ...

    async def history(self, run_id: str) -> list[RunSnapshot]:
        """Return every snapshot saved for ``run_id``, oldest first."""
        ...
