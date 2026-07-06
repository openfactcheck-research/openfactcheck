"""Composable wiring combinators over the graph primitives.

The nodes layer builds typed step nodes; this is its counterpart for the edges
between them. Rather than wire a graph edge by edge, describe its shape with a
few combinators that nest:

- [`chain`][chain] runs its parts one after another.
- [`per_item`][per_item] fans an iterable out to one branch per item, runs the
  body per item, and gathers the results back into a list.
- [`branch`][branch] routes a value to one of two paths by a predicate, both
  paths rejoining afterwards.
- [`loop`][loop] repeats a body while a predicate holds.

Each returns a [`Segment`][Segment], a fragment with one entry and its exits, and
segments nest inside one another, so a whole pipeline is composed from a handful
of calls. Spread a top-level segment into [`GraphBuilder.add`][GraphBuilder.add]
to register its wiring.

Example:
    ```python
    from openfactcheck.graph import GraphBuilder, chain, per_item

    g = GraphBuilder(input_type=Input, output_type=list[Verdict])
    cp, qg, rt, vf = ...  # step nodes
    g.add(*chain(g, g.start_node, cp, per_item(g, qg, rt, vf), g.end_node))
    graph = g.build()
    ```
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from openfactcheck.graph.builder import AnyGraphBuilder, WiringItem
from openfactcheck.graph.decision import Branch, Decision
from openfactcheck.graph.errors import GraphBuildError
from openfactcheck.graph.step import DestNode, EndNode, StartNode, Step

type Predicate = Callable[[Any], bool]
"""A test applied to a routed value, selecting a [`branch`][branch] path or stopping a [`loop`][loop]."""

type _SourceNode = Step[Any, Any, Any, Any] | StartNode[Any]
"""A node an ordinary edge may leave: a step or the start node."""

type _EntryNode = Step[Any, Any, Any, Any] | StartNode[Any] | EndNode[Any] | Decision[Any, Any, Any]
"""A node an inbound edge may land on when a segment is entered."""

type Part = Step[Any, Any, Any, Any] | StartNode[Any] | EndNode[Any] | Segment
"""A piece a combinator accepts: a node (step, start, or end) or a nested segment."""


# ---------------------------------------------------------------------------
# Segment model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _EdgeExit:
    """A segment exit reached by an ordinary edge, optionally gathering a fan-out."""

    node: _SourceNode
    collect: bool = False


@dataclass(frozen=True, slots=True)
class _DecisionExit:
    """A segment exit reached by a decision's default branch, as a [`loop`][loop] leaves its decision."""

    node: Decision[Any, Any, Any]


type _Exit = _EdgeExit | _DecisionExit
"""One point at which a segment hands its value onward."""


@dataclass(frozen=True, slots=True)
class Segment:
    """A composed graph fragment: one entry node, its internal wiring, and its exits.

    Produced by a combinator such as [`chain`][chain] or [`per_item`][per_item].
    Nest a segment inside another combinator to build up a shape, then spread the
    top-level one into [`GraphBuilder.add`][GraphBuilder.add] to register its
    edges (a segment iterates its own wiring, so ``g.add(*segment)`` works).
    """

    head: _EntryNode
    """The node an inbound edge lands on when this segment is entered."""

    mapped: bool
    """Whether the edge into [`head`][Segment.head] fans an iterable out per item."""

    exits: tuple[_Exit, ...]
    """The points at which this segment hands its value to whatever follows it."""

    edges: tuple[WiringItem, ...]
    """This segment's internal wiring, as items accepted by [`GraphBuilder.add`][GraphBuilder.add]."""

    def __iter__(self) -> Iterator[WiringItem]:
        """Iterate this segment's wiring items so a segment can be spread into ``add``."""
        return iter(self.edges)


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def _require_dest(node: _EntryNode) -> DestNode[Any, Any, Any]:
    """Return ``node`` as an edge destination, rejecting the start node.

    Raises:
        GraphBuildError: If ``node`` is the start node, which nothing routes into.
    """
    if isinstance(node, StartNode):
        raise GraphBuildError("the start node cannot be a destination; place it first in the chain")
    return node


def _connect(g: AnyGraphBuilder, source: _Exit, dest: _EntryNode, *, mapped: bool) -> WiringItem:
    """Build the wiring from one exit into an entry node.

    Honors ``mapped`` (fan the source's iterable out per item) and, for an edge
    exit, its ``collect`` (gather a fan-out's branches into a list). A decision
    exit routes its default branch to ``dest`` instead of drawing an edge.

    Raises:
        GraphBuildError: If ``dest`` is the start node, or a fan-out is asked for
            directly after a collect or straight out of a decision.
    """
    destination = _require_dest(dest)
    if isinstance(source, _DecisionExit):
        if mapped:
            raise GraphBuildError("cannot fan out directly from a decision; put a step between them")
        return Branch(source.node.id, destination.id, None)
    if source.collect and mapped:
        raise GraphBuildError(
            "cannot fan out immediately after a collect; put a step between the collect and the fan-out",
        )
    path = g.edge_from(source.node)
    if source.collect:
        return path.collect().to(destination)
    if mapped:
        return path.map().to(destination)
    return path.to(destination)


def _as_segment(part: Part) -> Segment:
    """Wrap a bare node as a single-node segment, or pass a segment through."""
    if isinstance(part, Segment):
        return part
    if isinstance(part, EndNode):
        return Segment(head=part, mapped=False, exits=(), edges=())
    return Segment(head=part, mapped=False, exits=(_EdgeExit(part),), edges=())


# ---------------------------------------------------------------------------
# Combinators
# ---------------------------------------------------------------------------


def chain(g: AnyGraphBuilder, *parts: Part) -> Segment:
    """Run parts one after another, wiring each to the next.

    Consecutive parts are joined with a plain edge, except where a neighbour asks
    otherwise: a [`per_item`][per_item] part is entered with a fan-out and left
    with a fan-in. Include [`start_node`][GraphBuilder] and
    [`end_node`][GraphBuilder] as the first and last parts to wire the whole
    graph in one call.

    Args:
        g: The builder the wiring is created on.
        parts: The nodes or nested segments to run in order.

    Returns:
        A segment entered at the first part and exiting from the last.

    Raises:
        GraphBuildError: If no parts are given.
    """
    if not parts:
        raise GraphBuildError("chain needs at least one part")
    segments = [_as_segment(part) for part in parts]
    edges: list[WiringItem] = list(segments[0].edges)
    for previous, current in pairwise(segments):
        edges.extend(_connect(g, exit_, current.head, mapped=current.mapped) for exit_ in previous.exits)
        edges.extend(current.edges)
    return Segment(
        head=segments[0].head,
        mapped=segments[0].mapped,
        exits=segments[-1].exits,
        edges=tuple(edges),
    )


def per_item(g: AnyGraphBuilder, *body: Part) -> Segment:
    """Fan an iterable out to one branch per item, run the body per item, and gather the results.

    The edge entering the returned segment fans the source's iterable output out
    to one parallel branch per item, the body runs on each item, and the edge
    leaving it collects the per-item results into a list in source order.

    Args:
        g: The builder the wiring is created on.
        body: The nodes or nested segments each item runs through, chained in order.

    Returns:
        A segment entered with a fan-out and left with a fan-in.

    Raises:
        GraphBuildError: If no body parts are given, or the body ends in a loop
            whose result cannot be gathered.
    """
    inner = chain(g, *body)
    exits: list[_Exit] = []
    for exit_ in inner.exits:
        if isinstance(exit_, _DecisionExit):
            raise GraphBuildError("a per_item body cannot end in a loop; put a step after the loop")
        exits.append(_EdgeExit(exit_.node, collect=True))
    return Segment(head=inner.head, mapped=True, exits=tuple(exits), edges=inner.edges)


def branch(  # noqa: PLR0913 - public combinator; each argument is distinct
    g: AnyGraphBuilder,
    condition: Predicate,
    then: Part,
    otherwise: Part,
    *,
    input_type: type[Any] = object,
    node_id: str | None = None,
) -> Segment:
    """Route a value to one of two paths by a predicate, both paths rejoining afterwards.

    The value entering the returned segment is tested by ``condition`` and sent
    down ``then`` when it holds or ``otherwise`` when it does not. Both paths exit
    to whatever follows the branch, so the graph rejoins after it.

    Args:
        g: The builder the wiring is created on.
        condition: The test applied to the routed value; a true result takes the
            ``then`` path.
        then: The path taken when ``condition`` holds.
        otherwise: The path taken when it does not.
        input_type: The type of value routed, recorded for the decision node.
        node_id: Identifier for the decision node; derived from the ``then`` path
            when omitted.

    Returns:
        A segment that routes at its entry and exits from both paths.

    Raises:
        GraphBuildError: If either path begins with a fan-out.
    """
    then_seg = _as_segment(then)
    otherwise_seg = _as_segment(otherwise)
    if then_seg.mapped or otherwise_seg.mapped:
        raise GraphBuildError("cannot route a decision into a fan-out; put a step before the per_item")
    decision = g.decision_node(input_type, node_id=node_id or f"branch:{then_seg.head.id}")
    edges: list[WiringItem] = [
        decision.when(condition, _require_dest(then_seg.head)),
        decision.otherwise(_require_dest(otherwise_seg.head)),
        *then_seg.edges,
        *otherwise_seg.edges,
    ]
    return Segment(head=decision, mapped=False, exits=(*then_seg.exits, *otherwise_seg.exits), edges=tuple(edges))


def loop(
    g: AnyGraphBuilder,
    *body: Part,
    until: Predicate,
    max_iterations: int | None = None,
    input_type: type[Any] = object,
    node_id: str | None = None,
) -> Segment:
    """Repeat a body until a predicate holds, then continue.

    The value entering the returned segment is tested by ``until``; while it does
    not hold, the value runs through the body and returns to the test, so the
    body must produce the same type it consumes. Once it holds, the value exits
    to whatever follows the loop.

    Args:
        g: The builder the wiring is created on.
        body: The nodes or nested segments run on each lap, chained in order.
        until: The test applied before each lap; the loop stops once it holds.
        max_iterations: The most laps allowed before the run fails, or ``None`` for
            no cap.
        input_type: The type of value routed, recorded for the decision node.
        node_id: Identifier for the decision node; derived from the body when omitted.

    Returns:
        A segment that repeats its body and exits once ``until`` holds.

    Raises:
        GraphBuildError: If no body parts are given, or the body begins with a fan-out.
    """
    body_seg = chain(g, *body)
    if body_seg.mapped:
        raise GraphBuildError("cannot route a decision into a fan-out; put a step before the per_item")
    decision = g.decision_node(input_type, node_id=node_id or f"loop:{body_seg.head.id}")
    edges: list[WiringItem] = [
        decision.when(lambda value: not until(value), _require_dest(body_seg.head), max_iterations=max_iterations),
        *body_seg.edges,
        *(_connect(g, exit_, decision, mapped=False) for exit_ in body_seg.exits),
    ]
    return Segment(head=decision, mapped=False, exits=(_DecisionExit(decision),), edges=tuple(edges))
