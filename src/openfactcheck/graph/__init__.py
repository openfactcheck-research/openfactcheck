"""Public API for the graph layer.

Build a graph of typed async nodes connected by edges, then run it to
completion. Assemble the graph with a [`GraphBuilder`][GraphBuilder], wire steps
with edges, call [`build`][GraphBuilder.build], and run the result with
[`Graph.run`][Graph.run] or its async peer [`Graph.arun`][Graph.arun]. Failures
raise [`GraphError`][GraphError] subclasses.

Import everything from ``openfactcheck.graph`` directly; submodule paths are
not part of the public API.

Example:
    ```python
    from openfactcheck.graph import GraphBuilder, StepContext

    g = GraphBuilder[None, None, str, dict]()


    @g.step
    async def extract(ctx: StepContext[None, None, str]) -> list[str]:
        return ctx.inputs.split()


    @g.step
    async def count(ctx: StepContext[None, None, list[str]]) -> dict:
        return {"n": len(ctx.inputs)}


    g.add(
        g.edge_from(g.start_node).to(extract),
        g.edge_from(extract).to(count),
        g.edge_from(count).to(g.end_node),
    )
    result = g.build().run("a b c", state=None, deps=None)
    ```
"""

from openfactcheck.graph.builder import EdgePathBuilder, GraphBuilder
from openfactcheck.graph.decision import Branch, Decision
from openfactcheck.graph.errors import (
    GraphBuildError,
    GraphError,
    GraphRuntimeError,
    GraphValidationError,
)
from openfactcheck.graph.graph import (
    DEFAULT_CONCURRENCY,
    ErrorPolicy,
    Graph,
    GraphStepper,
    RunOptions,
    StepResult,
)
from openfactcheck.graph.join import (
    ContextReducer,
    Join,
    Reducer,
    ReducerContext,
    reduce_dict_update,
    reduce_first,
    reduce_list_append,
    reduce_list_extend,
    reduce_null,
    reduce_sum,
)
from openfactcheck.graph.step import Edge, EdgeKind, EndNode, StartNode, Step, StepContext

# Builder and graph
__all__ = [
    "DEFAULT_CONCURRENCY",
    "EdgePathBuilder",
    "ErrorPolicy",
    "Graph",
    "GraphBuilder",
    "GraphStepper",
    "RunOptions",
    "StepResult",
]

# Nodes and edges
__all__ += [
    "Branch",
    "Decision",
    "Edge",
    "EdgeKind",
    "EndNode",
    "StartNode",
    "Step",
    "StepContext",
]

# Joins and reducers
__all__ += [
    "ContextReducer",
    "Join",
    "Reducer",
    "ReducerContext",
    "reduce_dict_update",
    "reduce_first",
    "reduce_list_append",
    "reduce_list_extend",
    "reduce_null",
    "reduce_sum",
]

# Errors
__all__ += [
    "GraphBuildError",
    "GraphError",
    "GraphRuntimeError",
    "GraphValidationError",
]
