"""Snapshot persistence for graph runs.

A run can save its state to a [`StateStore`][StateStore] after each task and be
resumed later, in the same process or a fresh one, from the last snapshot. A
[`RunSnapshot`][RunSnapshot] captures the run's frontier (the tasks still to run)
together with its join accumulators, loop counters, and shared state; run-scoped
dependencies are not persisted and are supplied again on resume.

Two stores ship: [`InMemoryStateStore`][InMemoryStateStore] keeps a per-run
history in memory (the default), and [`FileStateStore`][FileStateStore] persists
to disk for durability across processes.
"""

from openfactcheck.graph.persistence.file import FileStateStore
from openfactcheck.graph.persistence.in_memory import InMemoryStateStore
from openfactcheck.graph.persistence.protocols import (
    JoinSnapshot,
    PausePoint,
    RunSnapshot,
    RunStatus,
    StateStore,
    TaskSnapshot,
)

__all__ = [
    "FileStateStore",
    "InMemoryStateStore",
    "JoinSnapshot",
    "PausePoint",
    "RunSnapshot",
    "RunStatus",
    "StateStore",
    "TaskSnapshot",
]
