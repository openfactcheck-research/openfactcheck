"""Progress events emitted while a graph runs.

A run can be observed two ways, both yielding the same [`GraphEvent`][GraphEvent]
values: [`Graph.astream`][Graph.astream] yields them live as an async iterator,
and the ``on_event`` hook on [`RunOptions`][RunOptions] is called with each one
during [`Graph.arun`][Graph.arun]. A node start and finish (or failure) is
emitted per task, so a fanned-out collection reports one finish per item, and a
single run-finished event closes a successful run.

Match on the event class to handle each kind:

```python
match event:
    case NodeFinished(node_id=name, duration=seconds):
        ...
    case RunFinished(output=result):
        ...
```
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from openfactcheck.graph.forks import ForkStack


@dataclass(frozen=True, slots=True)
class NodeStarted:
    """A node's task has begun running."""

    node_id: str
    """Identifier of the node that started."""

    fork_stack: ForkStack
    """The fork branch the task belongs to."""

    type: Literal["node_started"] = "node_started"
    """Event tag identifying a node start."""


@dataclass(frozen=True, slots=True)
class NodeFinished:
    """A node's task finished successfully."""

    node_id: str
    """Identifier of the node that finished."""

    output: object
    """The value the node returned."""

    duration: float
    """Seconds the node's task took, including any retries."""

    fork_stack: ForkStack
    """The fork branch the task belonged to."""

    type: Literal["node_finished"] = "node_finished"
    """Event tag identifying a node finish."""


@dataclass(frozen=True, slots=True)
class NodeFailed:
    """A node's task raised after exhausting its retries."""

    node_id: str
    """Identifier of the node that failed."""

    error: Exception
    """The error the node raised."""

    duration: float
    """Seconds the node's task ran before failing, including any retries."""

    fork_stack: ForkStack
    """The fork branch the task belonged to."""

    type: Literal["node_failed"] = "node_failed"
    """Event tag identifying a node failure."""


@dataclass(frozen=True, slots=True)
class RunFinished:
    """The run completed and produced its terminal output."""

    output: object
    """The value routed into the end node."""

    type: Literal["run_finished"] = "run_finished"
    """Event tag identifying the end of a run."""


type GraphEvent = NodeStarted | NodeFinished | NodeFailed | RunFinished
"""Any progress event a run emits, distinguished by class or by its ``type`` tag."""

type GraphObserver = Callable[[GraphEvent], None]
"""A callback invoked with each [`GraphEvent`][GraphEvent] during a run."""
