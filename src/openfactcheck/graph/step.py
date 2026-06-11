"""Typed nodes, edges, and the per-invocation context for the graph layer.

A graph is built from nodes connected by edges. The work-bearing node is a
[`Step`][Step]: an async unit with one typed input and one typed output.
[`StartNode`][StartNode] and [`EndNode`][EndNode] mark where a run begins and
ends. Edges name a source and a destination by id.

A step's own function is fully statically typed (its
[`StepContext.inputs`][StepContext] and its return value). The wiring between
nodes is validated when the graph is built rather than by the type checker, so
the executor treats node inputs and outputs opaquely; see
[`GraphBuilder.build`][GraphBuilder] for the build-time checks.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

START_ID = "__start__"
"""Fixed identifier of every graph's start node."""

END_ID = "__end__"
"""Fixed identifier of every graph's end node."""


@dataclass(frozen=True, slots=True)
class StepContext[StateT, DepsT, InputT]:
    """Context passed to a step function on each invocation.

    Carries the node's typed ``inputs`` alongside the run-scoped ``state`` and
    the injected ``deps``, both shared across every node in a single run.

    Example:
        ```python
        async def extract(ctx: StepContext[None, Deps, str]) -> list[Claim]:
            client = ctx.deps.chat_client
            ...
        ```
    """

    inputs: InputT
    """The value flowing into this node along its incoming edge."""

    state: StateT
    """Run-scoped state shared across nodes for cross-cutting context."""

    deps: DepsT
    """Run-scoped dependencies (clients, configuration) injected into nodes."""


@dataclass(frozen=True, slots=True)
class Step[StateT, DepsT, InputT, OutputT]:
    """A typed async node: one input value in, one output value out.

    Created by [`GraphBuilder.step`][GraphBuilder] (usually as the ``@g.step``
    decorator), then referenced when wiring edges. The recorded ``input_type``
    and ``output_type`` are read from the wrapped function's annotations and
    used to validate edge compatibility at build time.
    """

    id: str
    """Stable identifier, taken from the wrapped function's name."""

    call: Callable[[StepContext[StateT, DepsT, InputT]], Awaitable[OutputT]]
    """The async function this node runs."""

    input_type: object | None
    """The declared input type, or ``None`` when it could not be read."""

    output_type: object | None
    """The declared output type, or ``None`` when it could not be read."""


@dataclass(frozen=True, slots=True)
class StartNode:
    """The graph's entry node; the graph input flows out of it."""

    id: str = START_ID
    """Fixed start-node identifier."""


@dataclass(frozen=True, slots=True)
class EndNode:
    """The graph's terminal node; the value routed into it is the graph output."""

    id: str = END_ID
    """Fixed end-node identifier."""


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed connection from one node to another, named by id."""

    source_id: str
    """Identifier of the node the edge leaves."""

    dest_id: str
    """Identifier of the node the edge enters."""


type AnyStep = Step[Any, Any, Any, Any]
"""A step with its type parameters erased, for the executor's wiring layer."""

type SourceNode = AnyStep | StartNode
"""A node an edge may leave: a step or the start node."""

type DestNode = AnyStep | EndNode
"""A node an edge may enter: a step or the end node."""
