"""Tests for building and running a linear graph."""

import asyncio

from openfactcheck.graph import GraphBuilder, StepContext


def _linear_builder() -> GraphBuilder[None, None, str, dict[str, int]]:
    g = GraphBuilder[None, None, str, dict[str, int]]()

    @g.step_node
    async def split(ctx: StepContext[None, None, str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def count(ctx: StepContext[None, None, list[str]]) -> dict[str, int]:
        return {"n": len(ctx.inputs)}

    g.add(
        g.edge_from(g.start_node).to(split),
        g.edge_from(split).to(count),
        g.edge_from(count).to(g.end_node),
    )
    return g


def test_Graph_run() -> None:
    graph = _linear_builder().build()

    result = graph.run("a b c", state=None, deps=None)

    assert result == {"n": 3}


def test_Graph_arun() -> None:
    graph = _linear_builder().build()

    result = asyncio.run(graph.arun("a b c d", state=None, deps=None))

    assert result == {"n": 4}


def test_StepContext_deps_injected() -> None:
    g = GraphBuilder[None, str, str, str]()

    @g.step_node
    async def use_deps(ctx: StepContext[None, str, str]) -> str:
        return f"{ctx.inputs}-{ctx.deps}"

    g.add(
        g.edge_from(g.start_node).to(use_deps),
        g.edge_from(use_deps).to(g.end_node),
    )

    result = g.build().run("x", state=None, deps="DEP")

    assert result == "x-DEP"
