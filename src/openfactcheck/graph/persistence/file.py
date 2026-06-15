"""A file-backed store that persists each run's snapshot history to disk."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from openfactcheck.graph.errors import GraphPersistenceError
from openfactcheck.graph.persistence._serde import PersistedSnapshot

if TYPE_CHECKING:
    from pathlib import Path

    from openfactcheck.graph.persistence.protocols import RunSnapshot


_SAFE_RUN_ID = re.compile(r"\A[A-Za-z0-9._-]+\Z")
"""A run id usable as one path component: letters, digits, dot, dash, underscore."""


class FileStateStore:
    """Persists run snapshots to disk so a run survives across processes.

    Each run's history is a single JSON file in the store directory. A save
    writes to a temporary file and atomically replaces the target, so a crash
    mid-write cannot corrupt the history.

    A run's values are stored as JSON, so any value it carries in its state must
    be JSON-serializable. A single run should have one writer at a time.
    """

    def __init__(self, directory: Path) -> None:
        """Persist runs under ``directory``, creating it if needed."""
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)

    async def save(self, snapshot: RunSnapshot) -> None:
        """Append ``snapshot`` to its run's history file, replacing it atomically."""
        history = await self.history(snapshot.run_id)
        history.append(snapshot)
        await asyncio.to_thread(self._write, snapshot.run_id, history)

    async def load(self, run_id: str) -> RunSnapshot | None:
        """Return the latest snapshot for ``run_id``, or ``None`` if there is none."""
        history = await self.history(run_id)
        return history[-1] if history else None

    async def history(self, run_id: str) -> list[RunSnapshot]:
        """Return every snapshot saved for ``run_id``, oldest first."""
        return await asyncio.to_thread(self._read, run_id)

    def _path(self, run_id: str) -> Path:
        """Map ``run_id`` to its snapshot file, refusing any id that could escape the store.

        Raises:
            GraphPersistenceError: If ``run_id`` is not a single safe path component.
        """
        if run_id in {".", ".."} or not _SAFE_RUN_ID.match(run_id):
            raise GraphPersistenceError(
                f"invalid run id {run_id!r}: a run id must match [A-Za-z0-9._-] and cannot be '.' or '..'"
            )
        directory = self._directory.resolve()
        path = (directory / f"{run_id}.json").resolve()
        if path.parent != directory:
            raise GraphPersistenceError(f"invalid run id {run_id!r}: resolves outside the store directory")
        return path

    def _read(self, run_id: str) -> list[RunSnapshot]:
        """Read a run's snapshot history from disk."""
        path = self._path(run_id)
        if not path.exists():
            return []
        return PersistedSnapshot.load_history(path.read_bytes())

    def _write(self, run_id: str, history: list[RunSnapshot]) -> None:
        """Write a run's snapshot history to disk atomically."""
        path = self._path(run_id)
        temp = path.with_name(f"{path.name}.tmp")
        temp.write_bytes(PersistedSnapshot.dump_history(history))
        temp.replace(path)
