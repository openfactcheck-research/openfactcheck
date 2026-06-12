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
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic

from openfactcheck.graph._typevars import DepsT, InputT, StateT
from openfactcheck.graph.join import Join

if TYPE_CHECKING:
    from openfactcheck.graph.decision import Decision
    from openfactcheck.graph.pause import Pause

START_ID = "__start__"
"""Fixed identifier of every graph's start node."""

END_ID = "__end__"
"""Fixed identifier of every graph's end node."""


@dataclass(frozen=True, slots=True)
class StepContext(Generic[InputT, StateT, DepsT]):
    """Context passed to a step function on each invocation.

    Carries the node's typed ``inputs`` alongside the run-scoped ``state`` and
    the injected ``deps``, both shared across every node in a single run.

    The type parameters, in order, are:

    1. ``InputT``: the type of ``inputs``, the value flowing into this node.
    2. ``StateT``: the type of ``state``, the run-scoped state shared across
       nodes. Optional; defaults to ``None`` when the graph keeps no state.
    3. ``DepsT``: the type of ``deps``, the read-only dependencies injected into
       nodes (clients, configuration). Optional; defaults to ``None``.

    A step annotates its single parameter with this context; the function's
    return type is the node's output. The output type is not a parameter here
    because it lives on the step's return annotation. State and deps may be
    omitted, so a step with neither annotates ``StepContext[str]``.

    Example:
        ```python
        # this node receives a str, with a Deps bag and no shared state.
        async def extract(ctx: StepContext[str, None, Deps]) -> list[Claim]:
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
class Step[InputT, OutputT, StateT, DepsT]:
    """A typed async node: one input value in, one output value out.

    Created by [`GraphBuilder.step_node`][GraphBuilder] (usually as the
    ``@g.step_node`` decorator), then referenced when wiring edges. The recorded
    ``input_type`` and ``output_type`` are read from the wrapped function's
    annotations and used to validate edge compatibility at build time.
    """

    id: str
    """Stable identifier, supplied to ``step_node`` or taken from the function's name."""

    call: Callable[[StepContext[InputT, StateT, DepsT]], Awaitable[OutputT]]
    """The async function this node runs."""

    input_type: object | None
    """The declared input type, or ``None`` when it could not be read."""

    output_type: object | None
    """The declared output type, or ``None`` when it could not be read."""

    retries: int = 0
    """How many extra attempts to make after the first if the call fails.

    Must be non-negative.
    """

    retry_backoff: float = 0.0
    """Base seconds to wait before a retry; the wait doubles each further attempt.

    Must be non-negative.
    """

    timeout: float | None = None
    """Seconds a single attempt may run before it is cancelled, or ``None`` for no limit.

    Must be positive when set.
    """


@dataclass(frozen=True, slots=True)
class StartNode[OutputT]:
    """The graph's entry node; the graph's input value flows out of it.

    Its type parameter is the graph input type, matched against the first
    step's input type when wiring the entry edge.
    """

    id: str = START_ID
    """Fixed start-node identifier."""


@dataclass(frozen=True, slots=True)
class EndNode[InputT]:
    """The graph's terminal node; the value routed into it is the graph output.

    Its type parameter is the graph output type, matched against the last
    step's output type when wiring the exit edge.
    """

    id: str = END_ID
    """Fixed end-node identifier."""

    if TYPE_CHECKING:
        # Pin InputT to a contravariant position so role-projection through
        # DestNode infers the variance edge type-checking relies on. Exists for
        # the type checker only; there is no such method at run time.
        def _accepts(self, value: InputT) -> None: ...


class EdgeKind(StrEnum):
    """How an edge delivers its source node's output to its destination."""

    PLAIN = "plain"
    """Deliver the whole output as one value to the destination."""

    MAP = "map"
    """Fan an iterable output out to one parallel branch per item."""


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed connection from one node to another, named by id."""

    source_id: str
    """Identifier of the node the edge leaves."""

    dest_id: str
    """Identifier of the node the edge enters."""

    kind: EdgeKind = EdgeKind.PLAIN
    """Whether the edge delivers the whole output or fans an iterable per item."""


type AnyStep = Step[Any, Any, Any, Any]
"""A step with its type parameters erased, for the executor's wiring layer."""

type SourceNode[OutputT, StateT, DepsT] = (
    Step[Any, OutputT, StateT, DepsT] | StartNode[OutputT] | Join[Any, OutputT] | Pause[Any, OutputT]
)
"""A node an edge may leave, projected to the output type it emits.

Lets [`GraphBuilder.edge_from`][GraphBuilder.edge_from] capture a source node's
output type regardless of what input the node accepts.
"""

type DestNode[InputT, StateT, DepsT] = (
    Step[InputT, Any, StateT, DepsT]
    | EndNode[InputT]
    | Join[InputT, Any]
    | Decision[InputT, StateT, DepsT]
    | Pause[InputT, Any]
)
"""A node an edge may enter, projected to the input type it accepts.

Lets [`EdgePathBuilder.to`][EdgePathBuilder.to] require a destination whose
input type the source node's output can feed, regardless of what the
destination emits.
"""
