"""Tests for rendering a graph as Mermaid flowchart source."""

from openfactcheck.graph import Graph, GraphBuilder, StepContext


def _graph_with_subgraph() -> Graph[str, str, None, None]:
    """An outer graph whose middle node is a subgraph embedding a small inner graph."""
    inner = GraphBuilder(input_type=str, output_type=str, name="inner")

    @inner.step_node
    async def first(ctx: StepContext[str]) -> str:
        return ctx.inputs

    @inner.step_node
    async def second(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    inner.add(
        inner.edge_from(inner.start_node).to(first),
        inner.edge_from(first).to(second),
        inner.edge_from(second).to(inner.end_node),
    )

    g = GraphBuilder(input_type=str, output_type=str, name="outer")

    @g.step_node
    async def pre(ctx: StepContext[str]) -> str:
        return ctx.inputs

    sub = g.subgraph_node(inner.build(), node_id="sub")
    g.add(
        g.edge_from(g.start_node).to(pre),
        g.edge_from(pre).to(sub),
        g.edge_from(sub).to(g.end_node),
    )
    return g.build()


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


def test_Graph_mermaid_collapses_subgraph_by_default() -> None:
    diagram = _graph_with_subgraph().to_mermaid()

    # The subgraph node is one opaque box; its inner nodes are not drawn.
    assert 'sub["sub"]' in diagram
    assert "subgraph " not in diagram
    assert "sub/" not in diagram
    assert "pre --> sub" in diagram
    assert "sub --> __end__" in diagram


def test_Graph_mermaid_expands_subgraph() -> None:
    diagram = _graph_with_subgraph().to_mermaid(expand_subgraphs=True)
    lines = diagram.splitlines()

    # The subgraph node becomes a cluster of its inner nodes.
    assert 'subgraph sub["sub"]' in diagram
    assert "    end" in lines
    # Inner ids are namespaced by the subgraph id; the visible label keeps the node's own id.
    assert 'sub/first["first"]' in diagram
    assert 'sub/second["second"]' in diagram
    assert "sub/first --> sub/second" in diagram
    # The subgraph's own start and end are hidden.
    assert "sub/__start__" not in diagram
    assert "sub/__end__" not in diagram
    # Edges attach to the inner nodes the flow enters and leaves, not the cluster border.
    assert "pre --> sub/first" in diagram
    assert "sub/second --> __end__" in diagram
    # A straight-line inner graph needs no ranking link: its exit is already its deepest node.
    assert "~~~" not in diagram
    # Only the outer start and end take the boundary style.
    assert "class __start__,__end__ boundary;" in diagram


def test_Graph_mermaid_expand_pins_successor_below_cyclic_subgraph() -> None:
    inner = GraphBuilder(input_type=str, output_type=str, name="loop")

    @inner.step_node
    async def seed(ctx: StepContext[str]) -> str:
        return ctx.inputs

    @inner.step_node
    async def fix(ctx: StepContext[str]) -> str:
        return ctx.inputs

    more = inner.decision_node(str, node_id="more")
    inner.add(
        inner.edge_from(inner.start_node).to(seed),
        inner.edge_from(seed).to(more),
        more.when(lambda value: len(value) > 0, fix, max_iterations=3),
        inner.edge_from(fix).to(more),
        more.otherwise(inner.end_node),
    )
    g = GraphBuilder(input_type=str, output_type=str, name="outer")
    loop = g.subgraph_node(inner.build(), node_id="loop")
    g.add(g.edge_from(g.start_node).to(loop), g.edge_from(loop).to(g.end_node))

    diagram = g.build().to_mermaid(expand_subgraphs=True)

    # The exit attaches to the decision node it leaves from.
    assert "loop/more --> __end__" in diagram
    # The loop body sits below the exit, so an invisible link pins the successor below the whole cluster.
    assert "loop/fix ~~~ __end__" in diagram
