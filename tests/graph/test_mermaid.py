"""Tests for rendering a graph as Mermaid flowchart source."""

from openfactcheck.graph import GraphBuilder, StepContext


def test_Graph_mermaid_renders_shapes_and_map_label() -> None:
    g = GraphBuilder[None, None, str, list[str]]()

    @g.step_node
    async def split(ctx: StepContext[None, None, str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def shout(ctx: StepContext[None, None, str]) -> str:
        return ctx.inputs.upper()

    gather = g.collect_node(str, node_id="gather")
    g.add(
        g.edge_from(g.start_node).to(split),
        g.edge_from(split).map().to(shout),
        g.edge_from(shout).to(gather),
        g.edge_from(gather).to(g.end_node),
    )

    diagram = g.build().to_mermaid(title="demo")

    assert "flowchart TD" in diagram
    assert "title: demo" in diagram
    assert '__start__(("start"))' in diagram
    assert '__end__(("end"))' in diagram
    assert 'split["split"]' in diagram
    assert 'gather{{"gather"}}' in diagram
    assert "split ==>|map| shout" in diagram
    assert "classDef boundary fill:#005355" in diagram
    assert "class __start__,__end__ boundary;" in diagram


def test_Graph_mermaid_renders_decision_and_pause() -> None:
    g = GraphBuilder[None, None, str, str]()

    @g.step_node
    async def classify(ctx: StepContext[None, None, str]) -> str:
        return ctx.inputs

    @g.step_node
    async def handle(ctx: StepContext[None, None, str]) -> str:
        return ctx.inputs

    dec = g.decision_node(str, node_id="route")
    review = g.pause_node(str, str, node_id="review")
    g.add(
        g.edge_from(g.start_node).to(classify),
        g.edge_from(classify).to(dec),
        dec.when_equals("x", handle),
        dec.otherwise(review),
        g.edge_from(handle).to(g.end_node),
        g.edge_from(review).to(g.end_node),
    )

    diagram = str(g.build())

    assert 'route{"route"}' in diagram
    assert 'review[/"review"/]' in diagram
    assert "route -.-> handle" in diagram
    assert "route -.-> review" in diagram
