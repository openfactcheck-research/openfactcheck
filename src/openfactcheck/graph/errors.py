"""Error hierarchy for the graph layer.

Every graph layer error derives from [`GraphError`][GraphError]. Failures
split by stage: assembling a graph ([`GraphBuildError`][GraphBuildError]),
validating its structure before a run
([`GraphValidationError`][GraphValidationError]), and executing it
([`GraphRuntimeError`][GraphRuntimeError]).

Catch the specific subclass for the stage you can recover from, or catch
[`GraphError`][GraphError] to handle every graph-layer failure in one place.
"""


class GraphError(Exception):
    """Base exception for every graph layer error.

    Catch this to handle any failure from building, validating, or running a
    [`Graph`][Graph] without branching on the specific cause.
    """


class GraphBuildError(GraphError):
    """A graph could not be assembled.

    Raised while wiring nodes and edges: a duplicate node identifier, an edge
    that references an unknown node, or a step registered more than once.
    """


class GraphValidationError(GraphError):
    """A graph's structure failed validation before running.

    Raised when finalizing a graph with no path from entry to exit,
    unreachable nodes, or an edge whose source output type cannot feed its
    destination input type.
    """


class GraphRuntimeError(GraphError):
    """A graph failed while running.

    Raised when a node raises, a loop exceeds its iteration bound, or a
    decision reaches no matching branch.
    """
