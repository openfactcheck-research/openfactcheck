"""An in-process store that keeps each run's snapshot history in memory."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openfactcheck.graph.persistence.protocols import RunSnapshot


class InMemoryStateStore:
    """Keeps a per-run snapshot history in memory.

    The default store: it deep-copies each snapshot on the way in and out, so
    later mutation of a run's state cannot corrupt saved history. Suitable for
    tests and for resuming within a single process; it does not survive restart.
    """

    def __init__(self) -> None:
        """Start with no saved runs."""
        self._runs: dict[str, list[RunSnapshot]] = {}

    async def save(self, snapshot: RunSnapshot) -> None:
        """Append a deep copy of ``snapshot`` to its run's history."""
        self._runs.setdefault(snapshot.run_id, []).append(copy.deepcopy(snapshot))

    async def load(self, run_id: str) -> RunSnapshot | None:
        """Return a deep copy of the latest snapshot for ``run_id``, or ``None``."""
        history = self._runs.get(run_id)
        if not history:
            return None
        return copy.deepcopy(history[-1])

    async def history(self, run_id: str) -> list[RunSnapshot]:
        """Return deep copies of every snapshot for ``run_id``, oldest first."""
        return [copy.deepcopy(snapshot) for snapshot in self._runs.get(run_id, [])]
