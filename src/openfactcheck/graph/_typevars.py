"""Shared type parameters for the graph layer's generic classes.

The four type variables that parameterize [`GraphBuilder`][GraphBuilder],
[`Graph`][Graph], and [`StepContext`][StepContext]. ``StateT`` and ``DepsT``
default to ``None``, so a graph that keeps no state or injects no dependencies
can omit them. ``infer_variance`` lets each follow the variance its use implies,
which the typed fan-out and edge projections rely on.
"""

from typing_extensions import TypeVar

InputT = TypeVar("InputT", infer_variance=True)
"""The value flowing into a node or graph."""

OutputT = TypeVar("OutputT", infer_variance=True)
"""The value a node or graph produces."""

StateT = TypeVar("StateT", default=None, infer_variance=True)
"""Run-scoped mutable state shared across nodes; defaults to ``None`` (no state)."""

DepsT = TypeVar("DepsT", default=None, infer_variance=True)
"""Read-only dependencies injected into nodes; defaults to ``None`` (no deps)."""
