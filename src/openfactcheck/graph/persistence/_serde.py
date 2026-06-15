"""JSON serialization for run snapshots.

A `RunSnapshot` round-trips through JSON, validated against the snapshot types
on load.

Most of it serializes directly, but its two maps are keyed by tuples (one key
embeds a fork stack), which JSON cannot use as object keys. Those maps are
carried as lists of entries on the wire and rebuilt on load.
"""

from pydantic import BaseModel, TypeAdapter

from openfactcheck.graph.forks import ForkStack
from openfactcheck.graph.persistence.protocols import (
    JoinSnapshot,
    PausePoint,
    RunSnapshot,
    RunStatus,
    TaskSnapshot,
)


class ReducerEntry(BaseModel):
    """One join accumulation, with its ``(join id, fork run id)`` key flattened."""

    join_id: str
    fork_run_id: str
    snapshot: JoinSnapshot


class LoopEntry(BaseModel):
    """One loop-branch count, with its ``(source, destination, fork stack)`` key flattened."""

    source: str
    dest: str
    fork_stack: ForkStack
    count: int


class PersistedSnapshot(BaseModel):
    """A run snapshot in its JSON-friendly form, with both tuple-keyed maps as lists."""

    run_id: str
    status: RunStatus
    pending: tuple[TaskSnapshot, ...]
    reducers: list[ReducerEntry]
    expected: dict[str, int]
    loops: list[LoopEntry]
    finalized: frozenset[tuple[str, str]]
    fork_seq: int
    has_final: bool
    final: object
    state: object
    paused: PausePoint | None

    @classmethod
    def from_snapshot(cls, snapshot: RunSnapshot) -> "PersistedSnapshot":
        """Flatten a run snapshot's tuple-keyed maps into the wire form."""
        return cls(
            run_id=snapshot.run_id,
            status=snapshot.status,
            pending=snapshot.pending,
            reducers=[
                ReducerEntry(join_id=join_id, fork_run_id=fork_run_id, snapshot=join)
                for (join_id, fork_run_id), join in snapshot.reducers.items()
            ],
            expected=snapshot.expected,
            loops=[
                LoopEntry(source=source, dest=dest, fork_stack=fork_stack, count=count)
                for (source, dest, fork_stack), count in snapshot.loops.items()
            ],
            finalized=snapshot.finalized,
            fork_seq=snapshot.fork_seq,
            has_final=snapshot.has_final,
            final=snapshot.final,
            state=snapshot.state,
            paused=snapshot.paused,
        )

    def to_snapshot(self) -> RunSnapshot:
        """Rebuild the run snapshot, restoring its tuple-keyed maps."""
        return RunSnapshot(
            run_id=self.run_id,
            status=self.status,
            pending=self.pending,
            reducers={(entry.join_id, entry.fork_run_id): entry.snapshot for entry in self.reducers},
            expected=self.expected,
            loops={(entry.source, entry.dest, entry.fork_stack): entry.count for entry in self.loops},
            finalized=self.finalized,
            fork_seq=self.fork_seq,
            has_final=self.has_final,
            final=self.final,
            state=self.state,
            paused=self.paused,
        )

    @staticmethod
    def dump_history(history: list[RunSnapshot]) -> bytes:
        """Serialize a run's snapshot history to JSON bytes."""
        return _HISTORY_ADAPTER.dump_json([PersistedSnapshot.from_snapshot(s) for s in history], indent=2)

    @staticmethod
    def load_history(data: bytes) -> list[RunSnapshot]:
        """Validate a run's snapshot history from JSON bytes."""
        return [persisted.to_snapshot() for persisted in _HISTORY_ADAPTER.validate_json(data)]


_HISTORY_ADAPTER: TypeAdapter[list[PersistedSnapshot]] = TypeAdapter(list[PersistedSnapshot])
"""Validates a run's snapshot history to and from a JSON array."""
