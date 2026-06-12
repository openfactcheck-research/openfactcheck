"""Tests for composing a built graph as a node inside another graph."""

from openfactcheck.graph import GraphBuilder, StepContext


def test_Graph_subgraph_runs_nested() -> None:
    inner_builder = GraphBuilder[None, None, str, str](name="inner")

    @inner_builder.step_node
    async def shout(ctx: StepContext[None, None, str]) -> str:
        return ctx.inputs.upper()

    inner_builder.add(
        inner_builder.edge_from(inner_builder.start_node).to(shout),
        inner_builder.edge_from(shout).to(inner_builder.end_node),
    )
    inner = inner_builder.build()

    outer = GraphBuilder[None, None, str, str]()

    @outer.step_node
    async def pre(ctx: StepContext[None, None, str]) -> str:
        return f"[{ctx.inputs}]"

    sub = outer.subgraph_node(inner, node_id="sub")

    @outer.step_node
    async def post(ctx: StepContext[None, None, str]) -> str:
        return f"{ctx.inputs}!"

    outer.add(
        outer.edge_from(outer.start_node).to(pre),
        outer.edge_from(pre).to(sub),
        outer.edge_from(sub).to(post),
        outer.edge_from(post).to(outer.end_node),
    )

    result = outer.build().run("hi", state=None, deps=None)

    assert result == "[HI]!"


def test_Graph_subgraph_shares_deps() -> None:
    inner_builder = GraphBuilder[None, str, str, str](name="inner")

    @inner_builder.step_node
    async def tag(ctx: StepContext[None, str, str]) -> str:
        return f"{ctx.inputs}/{ctx.deps}"

    inner_builder.add(
        inner_builder.edge_from(inner_builder.start_node).to(tag),
        inner_builder.edge_from(tag).to(inner_builder.end_node),
    )
    inner = inner_builder.build()

    outer = GraphBuilder[None, str, str, str]()
    sub = outer.subgraph_node(inner, node_id="sub")
    outer.add(
        outer.edge_from(outer.start_node).to(sub),
        outer.edge_from(sub).to(outer.end_node),
    )

    result = outer.build().run("x", state=None, deps="DEP")

    assert result == "x/DEP"
