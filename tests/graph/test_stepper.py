"""Tests for the step-by-step driver: manual advance and recover-by-override."""

import asyncio

from openfactcheck.graph import GraphBuilder, StepContext, reduce_list_append


def test_GraphStepper_advance_reports_each_step() -> None:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def upper(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    @g.step_node
    async def exclaim(ctx: StepContext[str]) -> str:
        return f"{ctx.inputs}!"

    g.add(
        g.edge_from(g.start_node).to(upper),
        g.edge_from(upper).to(exclaim),
        g.edge_from(exclaim).to(g.end_node),
    )
    graph = g.build()

    async def drive() -> tuple[list[str], str]:
        seen: list[str] = []
        async with graph.stepper("hi", state=None, deps=None) as run:
            while (step := await run.advance()) is not None:
                seen.append(step.node_id)
            return seen, run.output

    seen, output = asyncio.run(drive())

    assert seen == ["upper", "exclaim"]
    assert output == "HI!"


def test_GraphStepper_recover_overrides_failed_step() -> None:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def boom(ctx: StepContext[str]) -> str:
        raise RuntimeError("nope")

    @g.step_node
    async def finish(ctx: StepContext[str]) -> str:
        return f"recovered:{ctx.inputs}"

    g.add(
        g.edge_from(g.start_node).to(boom),
        g.edge_from(boom).to(finish),
        g.edge_from(finish).to(g.end_node),
    )
    graph = g.build()

    async def drive() -> str:
        async with graph.stepper("x", state=None, deps=None) as run:
            while (step := await run.advance()) is not None:
                if step.error is not None:
                    run.recover(step, "fallback")
            return run.output

    assert asyncio.run(drive()) == "recovered:fallback"


def test_GraphStepper_drop_drops_failed_branch() -> None:
    g = GraphBuilder[list[int], list[int]]()

    @g.step_node
    async def fan(ctx: StepContext[list[int]]) -> list[int]:
        return ctx.inputs

    @g.step_node
    async def double_unless_two(ctx: StepContext[int]) -> int:
        if ctx.inputs == 2:
            raise RuntimeError("two is bad")
        return ctx.inputs * 2

    collected = g.reduce_node(reduce_list_append, list, item_type=int, node_id="collected")
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(double_unless_two),
        g.edge_from(double_unless_two).to(collected),
        g.edge_from(collected).to(g.end_node),
    )
    graph = g.build()

    async def drive() -> list[int]:
        async with graph.stepper([1, 2, 3], state=None, deps=None) as run:
            while (step := await run.advance()) is not None:
                if step.error is not None:
                    run.drop(step)
            return run.output

    # The failing branch (2) is dropped; the join completes with the survivors.
    assert sorted(asyncio.run(drive())) == [2, 6]
