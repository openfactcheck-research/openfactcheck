"""Events emitted while a pipeline runs in streaming mode.

A streaming run yields these as it executes: a node starts and finishes for each
step, print output as it is produced, and a single terminal event carrying the
final result. They are the wire contract from the engine through the run
transport to the client, so each is a flat, JSON-serialisable record tagged by
``type``.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Event(BaseModel):
    """Base for run events: frozen and tagged by ``type``."""

    model_config = ConfigDict(frozen=True)


class NodeStartedEvent(_Event):
    """A pipeline step began running."""

    type: Literal["node_started"] = "node_started"
    node_id: str
    branch: int | None = None
    """Fan-out branch index when the step runs per item (for example one claim); unset otherwise."""


class NodeFinishedEvent(_Event):
    """A pipeline step finished running."""

    type: Literal["node_finished"] = "node_finished"
    node_id: str
    duration: float
    branch: int | None = None
    """Fan-out branch index when the step runs per item; unset otherwise."""

    output: object | None = None
    """A curated JSON payload for the step's result, included only for steps the run chooses to surface."""


class NodeFailedEvent(_Event):
    """A pipeline step raised an error."""

    type: Literal["node_failed"] = "node_failed"
    node_id: str
    error: str
    branch: int | None = None
    """Fan-out branch index when the step runs per item; unset otherwise."""


class NodeEmittedEvent(_Event):
    """A curated datum a step emitted from inside its task while running."""

    type: Literal["node_emitted"] = "node_emitted"
    node_id: str
    branch: int | None = None
    """Fan-out branch index when the step runs per item; unset otherwise."""

    data: object | None = None
    """A curated JSON payload the step emitted, for example a verifier's partial reasoning."""


class OutputEvent(_Event):
    """A line of print output produced during the run."""

    type: Literal["output"] = "output"
    text: str


class FinishedEvent(_Event):
    """The run completed, carrying its final captured output."""

    type: Literal["finished"] = "finished"
    success: bool
    output: str
    error: str | None = None


type RunEvent = NodeStartedEvent | NodeFinishedEvent | NodeFailedEvent | NodeEmittedEvent | OutputEvent | FinishedEvent
"""Any event a streaming run emits, distinguished by its ``type`` tag."""
