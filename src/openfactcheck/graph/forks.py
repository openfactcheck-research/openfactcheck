"""Fork-stack identity for fanned-out tasks.

When a run fans a value out to many parallel branches, each branch needs an
identity so its result can later be combined with its siblings at a join. That
identity is a [`ForkStack`][ForkStack]: a tuple of [`ForkStackItem`][ForkStackItem]
frames, one per enclosing fork, innermost fork last. A task at the root of the
graph carries the empty stack; every fan-out pushes a new frame.

Each frame pairs the fork's stable identifier with the identifier of the
specific firing that produced the branch, so repeated and nested fan-outs stay
distinct without collisions.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ForkStackItem:
    """One frame of a task's fork stack, identifying a single fanned-out branch."""

    fork_id: str
    """Identifier of the fork that created this branch, stable across runs."""

    fork_run_id: str
    """Identifier of the specific firing of that fork within one run."""

    branch_index: int
    """Position of this branch within its fork; the item index for a mapped collection."""


type ForkStack = tuple[ForkStackItem, ...]
"""A task's path through nested forks, innermost fork last; empty at the root."""
