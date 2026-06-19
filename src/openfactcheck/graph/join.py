"""Fan-in joins and the reducers that combine a fork's branch outputs.

A [`Join`][Join] gathers the outputs of a fanned-out subpath and folds them into
a single value with a reducer. A reducer takes the running accumulator and one
branch's value and returns the next accumulator; built-in reducers cover the
common shapes (collect into a list, merge dicts, sum, keep the first). A reducer
may instead take a [`ReducerContext`][ReducerContext] first, giving it the run's
state and dependencies and the ability to stop early once it has enough.

Joins are created through [`GraphBuilder.collect_node`][GraphBuilder.collect_node]
(ordered list collection) and [`GraphBuilder.reduce_node`][GraphBuilder.reduce_node]
(any reducer); this module holds the node type and the reducer library they draw on.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

type Reducer[AccT, ItemT] = Callable[[AccT, ItemT], AccT]
"""A fold over branch values: the running accumulator and one value give the next accumulator."""

type ContextReducer[StateT, DepsT, AccT, ItemT] = Callable[[ReducerContext[StateT, DepsT], AccT, ItemT], AccT]
"""A [`Reducer`][Reducer] that also receives the run's [`ReducerContext`][ReducerContext]."""

type NormalizedReducer = Callable[[ReducerContext[Any, Any], Any, Any], Any]
"""A reducer reduced to its context-taking form, ready for the executor to call uniformly."""


class ReducerContext[StateT, DepsT]:
    """The run context handed to a context-taking reducer.

    Carries the run-scoped ``state`` and injected ``deps``, and lets a reducer
    signal that it has seen enough and the remaining branches can be dropped.
    """

    def __init__(self, *, state: StateT, deps: DepsT) -> None:
        """Build a context exposing the run's state and dependencies."""
        self.state = state
        self.deps = deps
        self._stop = False

    def cancel_sibling_tasks(self) -> None:
        """Stop this fan-in early: emit the accumulator now and drop branches still in flight.

        Use it for first-acceptable-wins reducers. The branches already running
        finish but their values are discarded; their work is cancelled where the
        executor can.
        """
        self._stop = True

    @property
    def stopped(self) -> bool:
        """Whether a reducer asked to stop this fan-in early."""
        return self._stop


@dataclass(frozen=True, slots=True)
class Join[ItemT, AccT]:
    """A fan-in node that folds a fork's branch outputs into one value.

    Created by [`GraphBuilder.collect_node`][GraphBuilder.collect_node] or
    [`GraphBuilder.reduce_node`][GraphBuilder.reduce_node]. Wire it as the destination of a
    fanned-out subpath and as the source of the edge carrying the folded result,
    which flows on once every branch of the fork has arrived (or a reducer stops
    early).
    """

    id: str
    """Stable identifier of this join node."""

    verb: str
    """Short name of the fold operation, shown when the graph is rendered."""

    item_type: object | None
    """The per-branch input type, recorded for build-time edge validation."""

    reducer: NormalizedReducer
    """The fold applied to each branch's value, in context-taking form."""

    initial_factory: Callable[[], Any]
    """Builds the accumulator each time the join fires."""

    ordered: bool
    """Whether to fold branches in source order; otherwise in arrival order."""

    inline: bool = False
    """Whether the join was declared inline on an edge and renders without its own node."""

    if TYPE_CHECKING:
        # Pin ItemT to a contravariant position so a join reads as a valid edge
        # destination for its item type. Type-checker only; no runtime method.
        def _accepts(self, value: ItemT) -> None: ...


type AnyJoin = Join[Any, Any]
"""A join with its type parameters erased, for the executor's wiring layer."""


def reduce_list_append[T](acc: list[T], item: T) -> list[T]:
    """Append each branch's value to a list."""
    acc.append(item)
    return acc


def reduce_list_extend[T](acc: list[T], item: Iterable[T]) -> list[T]:
    """Extend a list with each branch's iterable of values."""
    acc.extend(item)
    return acc


def reduce_dict_update[K, V](acc: dict[K, V], item: Mapping[K, V]) -> dict[K, V]:
    """Merge each branch's mapping into one dict, later branches winning on key clashes."""
    acc.update(item)
    return acc


def reduce_sum(acc: float, item: float) -> float:
    """Add each branch's number to a running total."""
    return acc + item


def reduce_null[AccT](acc: AccT, item: object) -> AccT:  # noqa: ARG001 - discards the value by design.
    """Discard every branch's value, leaving the initial accumulator unchanged."""
    return acc


def reduce_first[ItemT](ctx: ReducerContext[Any, Any], acc: ItemT | None, item: ItemT) -> ItemT:  # noqa: ARG001 - acc is the unused running value.
    """Keep the first branch's value and stop, dropping the rest."""
    ctx.cancel_sibling_tasks()
    return item
