"""Conditional branching: route one value to one of several downstream paths.

A [`Decision`][Decision] node inspects the value routed into it and forwards it to
the first branch whose condition matches, or to a default branch. Conditions
match on a predicate, the value's type, or equality. Branches are tried in the
order they are added; the first match wins, and a value that matches no branch
and has no default fails the run.

Wire a decision as the destination of the edge carrying the value to route, then
add its branches with [`when`][Decision.when], [`when_type`][Decision.when_type],
[`when_equals`][Decision.when_equals], and [`otherwise`][Decision.otherwise].
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from openfactcheck.graph.step import DestNode

type Matcher = Callable[[object], bool]
"""Tests whether a value should take a given branch."""


@dataclass(frozen=True, slots=True)
class Branch:
    """One ordered branch of a decision: a condition and where it routes.

    Produced by a [`Decision`][Decision]'s branch methods and registered with
    [`GraphBuilder.add`][GraphBuilder.add]. A ``None`` condition marks the
    default branch.
    """

    source_id: str
    """Identifier of the decision the branch leaves."""

    dest_id: str
    """Identifier of the node the branch routes to."""

    condition: Matcher | None
    """The test that selects this branch, or ``None`` for the default branch."""

    max_iterations: int | None = None
    """For a branch that loops back to an earlier node, the most times it may be taken before the run fails."""


class Decision[StateT, DepsT, InputT]:
    """A routing node that forwards its input to the first matching branch.

    Created by [`GraphBuilder.decision`][GraphBuilder.decision]. Its type
    parameter is the type of the value it routes, matched against the output of
    the edge feeding it.
    """

    def __init__(self, *, node_id: str, input_type: object | None) -> None:
        """Create a decision node that routes values of one type."""
        self.id = node_id
        self.input_type = input_type

    def when(
        self,
        predicate: Callable[[InputT], bool],
        dest: DestNode[StateT, DepsT, Any],
        *,
        max_iterations: int | None = None,
    ) -> Branch:
        """Route to ``dest`` when ``predicate`` returns true for the value.

        Args:
            predicate: Test applied to the routed value.
            dest: The node this branch routes to.
            max_iterations: When this branch loops back to an earlier node, the
                most times it may be taken before the run fails.

        Returns:
            The branch to register with [`GraphBuilder.add`][GraphBuilder.add].
        """
        return Branch(self.id, dest.id, cast("Matcher", predicate), max_iterations)

    def when_type(
        self,
        cls: type,
        dest: DestNode[StateT, DepsT, Any],
        *,
        max_iterations: int | None = None,
    ) -> Branch:
        """Route to ``dest`` when the value is an instance of ``cls``.

        Args:
            cls: Type the value is tested against with ``isinstance``.
            dest: The node this branch routes to.
            max_iterations: When this branch loops back to an earlier node, the
                most times it may be taken before the run fails.

        Returns:
            The branch to register with [`GraphBuilder.add`][GraphBuilder.add].
        """
        return Branch(self.id, dest.id, lambda value: isinstance(value, cls), max_iterations)

    def when_equals(
        self,
        expected: object,
        dest: DestNode[StateT, DepsT, Any],
        *,
        max_iterations: int | None = None,
    ) -> Branch:
        """Route to ``dest`` when the value equals ``expected``.

        Args:
            expected: Value compared against the routed value with ``==``.
            dest: The node this branch routes to.
            max_iterations: When this branch loops back to an earlier node, the
                most times it may be taken before the run fails.

        Returns:
            The branch to register with [`GraphBuilder.add`][GraphBuilder.add].
        """
        return Branch(self.id, dest.id, lambda value: value == expected, max_iterations)

    def otherwise(self, dest: DestNode[StateT, DepsT, Any], *, max_iterations: int | None = None) -> Branch:
        """Route to ``dest`` when no other branch matched.

        Args:
            dest: The node values reaching no other branch route to.
            max_iterations: When this branch loops back to an earlier node, the
                most times it may be taken before the run fails.

        Returns:
            The default branch to register with [`GraphBuilder.add`][GraphBuilder.add].
        """
        return Branch(self.id, dest.id, None, max_iterations)

    if TYPE_CHECKING:
        # Pin InputT to a contravariant position so a decision reads as a valid
        # edge destination for its input type. Type-checker only; no runtime method.
        def _accepts(self, value: InputT) -> None: ...


type AnyDecision = Decision[Any, Any, Any]
"""A decision with its type parameters erased, for the executor's wiring layer."""
