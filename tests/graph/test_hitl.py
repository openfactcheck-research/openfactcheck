"""Tests for human-in-the-loop pause and resume."""

import pytest

from openfactcheck.graph import (
    GraphBuilder,
    GraphPaused,
    InMemoryStateStore,
    RunOptions,
    StepContext,
)


def _review_graph() -> GraphBuilder[str, str]:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def draft(ctx: StepContext[str]) -> str:
        return f"draft of {ctx.inputs}"

    approval = g.pause_node(str, str, node_id="approval", prompt="Approve this draft?")

    @g.step_node
    async def finalize(ctx: StepContext[str]) -> str:
        return f"published: {ctx.inputs}"

    g.add(
        g.edge_from(g.start_node).to(draft),
        g.edge_from(draft).to(approval),
        g.edge_from(approval).to(finalize),
        g.edge_from(finalize).to(g.end_node),
    )
    return g


def test_Graph_run_pauses_at_pause_node() -> None:
    store = InMemoryStateStore()
    graph = _review_graph().build()

    with pytest.raises(GraphPaused) as caught:
        graph.run("report", state=None, deps=None, options=RunOptions(store=store, run_id="doc1"))

    assert caught.value.context == "draft of report"
    assert caught.value.prompt == "Approve this draft?"
    assert caught.value.run_id == "doc1"


def test_Graph_resume_with_injects_answer() -> None:
    store = InMemoryStateStore()
    graph = _review_graph().build()

    with pytest.raises(GraphPaused):
        graph.run("report", state=None, deps=None, options=RunOptions(store=store, run_id="doc2"))

    result = graph.resume_with("doc2", store=store, deps=None, value="approved draft of report")

    assert result == "published: approved draft of report"
