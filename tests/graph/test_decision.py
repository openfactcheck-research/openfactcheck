"""Tests for conditional branching: predicate, type, equality, default, no-match."""

import pytest

from openfactcheck.graph import GraphBuilder, GraphRuntimeError, StepContext


def test_Graph_decision_routes_by_predicate() -> None:
    g = GraphBuilder[None, None, int, str]()

    @g.step
    async def classify(ctx: StepContext[None, None, int]) -> int:
        return ctx.inputs

    @g.step
    async def big(ctx: StepContext[None, None, int]) -> str:
        return f"big:{ctx.inputs}"

    @g.step
    async def small(ctx: StepContext[None, None, int]) -> str:
        return f"small:{ctx.inputs}"

    dec = g.decision(int)
    g.add(
        g.edge_from(g.start_node).to(classify),
        g.edge_from(classify).to(dec),
        dec.when(lambda n: n >= 10, big),
        dec.otherwise(small),
        g.edge_from(big).to(g.end_node),
        g.edge_from(small).to(g.end_node),
    )
    graph = g.build()

    assert graph.run(42, state=None, deps=None) == "big:42"
    assert graph.run(3, state=None, deps=None) == "small:3"


def test_Graph_decision_routes_by_type() -> None:
    g = GraphBuilder[None, None, object, str]()

    @g.step
    async def identity(ctx: StepContext[None, None, object]) -> object:
        return ctx.inputs

    @g.step
    async def handle_int(ctx: StepContext[None, None, object]) -> str:
        return f"int:{ctx.inputs}"

    @g.step
    async def handle_str(ctx: StepContext[None, None, object]) -> str:
        return f"str:{ctx.inputs}"

    dec = g.decision(object)
    g.add(
        g.edge_from(g.start_node).to(identity),
        g.edge_from(identity).to(dec),
        dec.when_type(int, handle_int),
        dec.when_type(str, handle_str),
        g.edge_from(handle_int).to(g.end_node),
        g.edge_from(handle_str).to(g.end_node),
    )
    graph = g.build()

    assert graph.run(5, state=None, deps=None) == "int:5"
    assert graph.run("x", state=None, deps=None) == "str:x"


def test_Graph_decision_when_equals() -> None:
    g = GraphBuilder[None, None, str, str]()

    @g.step
    async def echo(ctx: StepContext[None, None, str]) -> str:
        return ctx.inputs

    @g.step
    async def matched(ctx: StepContext[None, None, str]) -> str:
        return "matched"

    @g.step
    async def other(ctx: StepContext[None, None, str]) -> str:
        return "other"

    dec = g.decision(str)
    g.add(
        g.edge_from(g.start_node).to(echo),
        g.edge_from(echo).to(dec),
        dec.when_equals("ping", matched),
        dec.otherwise(other),
        g.edge_from(matched).to(g.end_node),
        g.edge_from(other).to(g.end_node),
    )
    graph = g.build()

    assert graph.run("ping", state=None, deps=None) == "matched"
    assert graph.run("pong", state=None, deps=None) == "other"


def test_Graph_decision_no_match_raises() -> None:
    g = GraphBuilder[None, None, int, str]()

    @g.step
    async def classify(ctx: StepContext[None, None, int]) -> int:
        return ctx.inputs

    @g.step
    async def only_big(ctx: StepContext[None, None, int]) -> str:
        return "big"

    dec = g.decision(int)
    g.add(
        g.edge_from(g.start_node).to(classify),
        g.edge_from(classify).to(dec),
        dec.when(lambda n: n >= 10, only_big),
        g.edge_from(only_big).to(g.end_node),
    )
    graph = g.build()

    with pytest.raises(GraphRuntimeError):
        graph.run(3, state=None, deps=None)
