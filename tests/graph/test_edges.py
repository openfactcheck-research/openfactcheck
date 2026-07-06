"""Tests for the composition combinators: chain, per_item, branch, and loop."""

import pytest

from openfactcheck.graph import GraphBuilder, GraphBuildError, StepContext, branch, chain, loop, per_item, to_mermaid


def test_chain_runs_parts_in_order() -> None:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def first(ctx: StepContext[str]) -> str:
        return ctx.inputs + "-first"

    @g.step_node
    async def second(ctx: StepContext[str]) -> str:
        return ctx.inputs + "-second"

    g.add(*chain(g, g.start_node, first, second, g.end_node))

    result = g.build().run("x", state=None, deps=None)

    assert result == "x-first-second"


def test_per_item_fans_out_and_collects_in_source_order() -> None:
    g = GraphBuilder[str, list[str]]()

    @g.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def shout(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    g.add(*chain(g, g.start_node, split, per_item(g, shout), g.end_node))

    result = g.build().run("a b c", state=None, deps=None)

    assert result == ["A", "B", "C"]


def test_per_item_runs_a_multi_step_body_per_item() -> None:
    g = GraphBuilder[str, list[str]]()

    @g.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def shout(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    @g.step_node
    async def exclaim(ctx: StepContext[str]) -> str:
        return ctx.inputs + "!"

    g.add(*chain(g, g.start_node, split, per_item(g, shout, exclaim), g.end_node))

    result = g.build().run("a b", state=None, deps=None)

    assert result == ["A!", "B!"]


def test_chain_and_per_item_match_a_hand_wired_graph() -> None:
    """The combinators produce the same wiring as building the graph edge by edge."""
    hand = GraphBuilder[str, list[str]]()

    @hand.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @hand.step_node
    async def shout(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    hand.add(
        hand.edge_from(hand.start_node).to(split),
        hand.edge_from(split).map().to(shout),
        hand.edge_from(shout).collect().to(hand.end_node),
    )

    composed = GraphBuilder[str, list[str]]()

    @composed.step_node
    async def split(ctx: StepContext[str]) -> list[str]:  # noqa: F811 - parallel graph, same node ids by design.
        return ctx.inputs.split()

    @composed.step_node
    async def shout(ctx: StepContext[str]) -> str:  # noqa: F811 - parallel graph, same node ids by design.
        return ctx.inputs.upper()

    composed.add(*chain(composed, composed.start_node, split, per_item(composed, shout), composed.end_node))

    assert to_mermaid(composed.build().spec) == to_mermaid(hand.build().spec)


def test_chain_no_parts_raises() -> None:
    g = GraphBuilder[str, str]()

    with pytest.raises(GraphBuildError, match="at least one part"):
        chain(g)


def test_per_item_directly_after_a_collect_raises() -> None:
    g = GraphBuilder[str, list[str]]()

    @g.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def shout(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    @g.step_node
    async def echo(ctx: StepContext[str]) -> list[str]:
        return [ctx.inputs]

    with pytest.raises(GraphBuildError, match="fan out immediately after a collect"):
        chain(g, g.start_node, split, per_item(g, shout), per_item(g, echo), g.end_node)


def test_loop_repeats_until_the_predicate_holds() -> None:
    g = GraphBuilder[int, int]()

    @g.step_node
    async def decrement(ctx: StepContext[int]) -> int:
        return ctx.inputs - 1

    g.add(*chain(g, g.start_node, loop(g, decrement, until=lambda n: n <= 0), g.end_node))

    result = g.build().run(3, state=None, deps=None)

    assert result == 0


def test_loop_over_a_multi_step_body() -> None:
    g = GraphBuilder[int, int]()

    @g.step_node
    async def halve(ctx: StepContext[int]) -> int:
        return ctx.inputs // 2

    @g.step_node
    async def drop_one(ctx: StepContext[int]) -> int:
        return ctx.inputs - 1

    g.add(*chain(g, g.start_node, loop(g, halve, drop_one, until=lambda n: n <= 0), g.end_node))

    result = g.build().run(10, state=None, deps=None)

    # 10 -> 5 -> 4 (lap), 4 -> 2 -> 1 (lap), 1 -> 0 -> -1 (lap), -1 stops.
    assert result == -1


def test_branch_routes_by_predicate_and_rejoins() -> None:
    g = GraphBuilder[int, str]()

    @g.step_node
    async def positive(ctx: StepContext[int]) -> str:
        return "positive"

    @g.step_node
    async def nonpositive(ctx: StepContext[int]) -> str:
        return "nonpositive"

    @g.step_node
    async def wrap(ctx: StepContext[str]) -> str:
        return f"[{ctx.inputs}]"

    g.add(*chain(g, g.start_node, branch(g, lambda n: n > 0, positive, nonpositive), wrap, g.end_node))
    graph = g.build()

    assert graph.run(5, state=None, deps=None) == "[positive]"
    assert graph.run(-1, state=None, deps=None) == "[nonpositive]"


def test_fan_out_directly_from_a_loop_raises() -> None:
    g = GraphBuilder[int, list[int]]()

    @g.step_node
    async def decrement(ctx: StepContext[int]) -> int:
        return ctx.inputs - 1

    @g.step_node
    async def spread(ctx: StepContext[int]) -> list[int]:
        return [ctx.inputs]

    with pytest.raises(GraphBuildError, match="fan out directly from a decision"):
        chain(g, g.start_node, loop(g, decrement, until=lambda n: n <= 0), per_item(g, spread), g.end_node)


def test_per_item_ending_in_a_loop_raises() -> None:
    g = GraphBuilder[str, list[int]]()

    @g.step_node
    async def to_int(ctx: StepContext[str]) -> int:
        return int(ctx.inputs)

    @g.step_node
    async def decrement(ctx: StepContext[int]) -> int:
        return ctx.inputs - 1

    with pytest.raises(GraphBuildError, match="per_item body cannot end in a loop"):
        per_item(g, to_int, loop(g, decrement, until=lambda n: n <= 0))
