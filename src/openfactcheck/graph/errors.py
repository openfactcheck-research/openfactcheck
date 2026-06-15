"""Error hierarchy for the graph layer.

Every graph layer error derives from [`GraphError`][GraphError]. Failures
split by stage: assembling a graph ([`GraphBuildError`][GraphBuildError]),
validating its structure before a run
([`GraphValidationError`][GraphValidationError]), executing it
([`GraphRuntimeError`][GraphRuntimeError]), saving or loading a run snapshot
([`GraphPersistenceError`][GraphPersistenceError]), and rendering its diagram to
an image ([`GraphRenderError`][GraphRenderError]).

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


class GraphPersistenceError(GraphError):
    """A run's snapshot could not be saved or loaded.

    Raised when a store is given a run id it cannot map to a safe location, or
    when a stored snapshot cannot be read back into a run.
    """


class GraphRenderError(GraphError):
    """A graph diagram could not be rendered to an image.

    Raised when the rendering service cannot be reached or returns an error, or
    the diagram is too large for the request. The Mermaid source is always
    available from [`Graph.to_mermaid`][Graph.to_mermaid] regardless.
    """


class GraphPaused(GraphError):  # noqa: N818 - a control-flow signal, not a failure; "Error" suffix would mislead.
    """A run reached a pause node and is waiting for external input.

    Not a failure: the run snapshotted its state and stopped at a pause node.
    Inspect ``context`` and ``prompt`` to learn what is being asked, then
    continue with [`Graph.resume_with`][Graph.resume_with], supplying the answer.
    """

    def __init__(self, message: str, *, node_id: str, context: object, prompt: str | None, run_id: str | None) -> None:
        """Record where the run paused and what it is asking for."""
        self.node_id = node_id
        self.context = context
        self.prompt = prompt
        self.run_id = run_id
        super().__init__(message)
