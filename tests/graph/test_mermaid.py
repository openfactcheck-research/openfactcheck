"""Tests for rendering a graph as Mermaid flowchart source."""

from openfactcheck.graph import GraphBuilder, StepContext


def test_Graph_mermaid_renders_shapes_and_fanout_fanin_labels() -> None:
    g = GraphBuilder[str, list[str]]()

    @g.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def shout(ctx: StepContext[str]) -> str:
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
    assert "shout -->|collect| gather" in diagram
    assert "classDef boundary fill:#005355" in diagram
    assert "class __start__,__end__ boundary;" in diagram


def test_Graph_mermaid_collapses_inline_collect() -> None:
    g = GraphBuilder[str, list[str]]()

    @g.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def shout(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    @g.step_node
    async def gather(ctx: StepContext[list[str]]) -> list[str]:
        return ctx.inputs

    g.add(
        g.edge_from(g.start_node).to(split),
        g.edge_from(split).map().to(shout),
        g.edge_from(shout).collect().to(gather),
        g.edge_from(gather).to(g.end_node),
    )

    diagram = g.build().to_mermaid()

    # The inline collect renders as a labeled edge straight to its successor, with no node of its own.
    assert "shout -->|collect| gather" in diagram
    assert "{{" not in diagram  # no hexagon: the inline join has no node
    assert "collect:shout->gather" not in diagram  # the inline join id is never emitted


def test_Graph_mermaid_show_types_labels_edges() -> None:
    g = GraphBuilder(input_type=str, output_type=list[str])

    @g.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def shout(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    @g.step_node
    async def gather(ctx: StepContext[list[str]]) -> list[str]:
        return ctx.inputs

    g.add(
        g.edge_from(g.start_node).to(split),
        g.edge_from(split).map().to(shout),
        g.edge_from(shout).collect().to(gather),
        g.edge_from(gather).to(g.end_node),
    )

    diagram = g.build().to_mermaid(show_types=True)

    assert '__start__ -->|"str"| split' in diagram  # the graph input type
    assert 'split ==>|"map: list[str]"| shout' in diagram  # map carries the source's iterable
    assert 'shout -->|"collect: list[str]"| gather' in diagram  # collect gathers str into list[str]
    assert 'gather -->|"list[str]"| __end__' in diagram  # the source's output type


def test_Graph_mermaid_labels_reduce_node() -> None:
    g = GraphBuilder[str, int]()

    @g.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def size(ctx: StepContext[str]) -> int:
        return len(ctx.inputs)

    total = g.reduce_node(lambda acc, item: acc + item, lambda: 0, item_type=int, node_id="total")
    g.add(
        g.edge_from(g.start_node).to(split),
        g.edge_from(split).map().to(size),
        g.edge_from(size).to(total),
        g.edge_from(total).to(g.end_node),
    )

    diagram = g.build().to_mermaid()

    assert "size -->|reduce| total" in diagram


def test_Graph_mermaid_renders_decision_and_pause() -> None:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def classify(ctx: StepContext[str]) -> str:
        return ctx.inputs

    @g.step_node
    async def handle(ctx: StepContext[str]) -> str:
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
