"""Tests for graph build-time validation."""

import pytest

from openfactcheck.graph import (
    Edge,
    GraphBuildError,
    GraphBuilder,
    GraphValidationError,
    StepContext,
)


async def _echo(ctx: StepContext[None, None, str]) -> str:
    return ctx.inputs


async def _echo_other(ctx: StepContext[None, None, str]) -> str:
    return ctx.inputs


def test_GraphBuilder_step_duplicate() -> None:
    g = GraphBuilder[None, None, str, str]()
    g.step(_echo)

    with pytest.raises(GraphBuildError):
        g.step(_echo)


def test_GraphBuilder_build_unknown_node() -> None:
    g = GraphBuilder[None, None, str, str]()
    echo = g.step(_echo)
    g.add(
        g.edge_from(g.start_node).to(echo),
        Edge(source_id="ghost", dest_id=echo.id),
    )

    with pytest.raises(GraphBuildError):
        g.build()


def test_GraphBuilder_build_no_entry() -> None:
    g = GraphBuilder[None, None, str, str]()
    echo = g.step(_echo)
    g.add(g.edge_from(echo).to(g.end_node))

    with pytest.raises(GraphValidationError):
        g.build()


def test_GraphBuilder_build_unreachable() -> None:
    g = GraphBuilder[None, None, str, str]()
    reached = g.step(_echo)
    stranded = g.step(_echo_other)
    g.add(
        g.edge_from(g.start_node).to(reached),
        g.edge_from(reached).to(g.end_node),
        g.edge_from(stranded).to(g.end_node),
    )

    with pytest.raises(GraphValidationError):
        g.build()


def test_GraphBuilder_build_type_mismatch() -> None:
    g = GraphBuilder[None, None, str, int]()

    @g.step
    async def produce(ctx: StepContext[None, None, str]) -> int:
        return len(ctx.inputs)

    @g.step
    async def consume(ctx: StepContext[None, None, str]) -> int:
        return len(ctx.inputs)

    g.add(
        g.edge_from(g.start_node).to(produce),
        g.edge_from(produce).to(consume),
        g.edge_from(consume).to(g.end_node),
    )

    with pytest.raises(GraphValidationError):
        g.build()
