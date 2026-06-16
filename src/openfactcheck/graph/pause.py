"""A node that suspends a run to await external or human input.

When a run reaches a [`Pause`][Pause] node, it snapshots its state and stops,
raising [`GraphPaused`][openfactcheck.graph.errors.GraphPaused] with the value
that arrived (the context for whoever answers) and an optional prompt. The run
continues with [`Graph.resume_with`][Graph.resume_with], whose supplied value
becomes the pause node's output and flows to its successor.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any


@dataclass(frozen=True, slots=True)
class Pause[ContextT, AnswerT]:
    """A node that suspends a run until an answer is supplied on resume.

    Created by [`GraphBuilder.pause_node`][GraphBuilder.pause_node]. Its first type
    parameter is the context type that flows in (what the pauser sees); its
    second is the answer type supplied on resume, which becomes the node's output.
    """

    id: str
    """Stable identifier of this pause node."""

    context_type: object | None
    """The type flowing in, recorded for build-time edge validation."""

    answer_type: object | None
    """The type supplied on resume, recorded for build-time edge validation."""

    prompt: str | None
    """A human-readable description of what is being asked, surfaced on pause."""

    if TYPE_CHECKING:
        # Pin ContextT to a contravariant position so a pause reads as a valid
        # edge destination for its context type. Type-checker only; no runtime method.
        def _accepts(self, value: ContextT) -> None: ...


type AnyPause = Pause[Any, Any]
"""A pause with its type parameters erased, for the executor's wiring layer."""
