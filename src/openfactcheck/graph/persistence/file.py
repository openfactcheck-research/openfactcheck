"""A file-backed store that persists each run's snapshot history to disk."""

from __future__ import annotations

import asyncio
import pickle
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from openfactcheck.graph.persistence.protocols import RunSnapshot


class FileStateStore:
    """Persists run snapshots to disk so a run survives across processes.

    Each run's history is a single file in the store directory. A save writes to
    a temporary file and atomically replaces the target, so a crash mid-write
    cannot corrupt the history.

    Snapshots are stored with ``pickle`` so any node value can be persisted, not
    only JSON-friendly ones. Because unpickling can execute arbitrary code, only
    load from a directory you trust. A single run should have one writer at a
    time.
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

    def _read(self, run_id: str) -> list[RunSnapshot]:
        """Read a run's snapshot history from disk."""
        path = self._directory / f"{run_id}.pickle"
        if not path.exists():
            return []
        return pickle.loads(path.read_bytes())  # noqa: S301 - snapshots come from a trusted directory; see class docs.

    def _write(self, run_id: str, history: list[RunSnapshot]) -> None:
        """Write a run's snapshot history to disk atomically."""
        path = self._directory / f"{run_id}.pickle"
        temp = path.with_name(f"{path.name}.tmp")
        temp.write_bytes(pickle.dumps(history))
        temp.replace(path)
