"""Render a graph definition as a Mermaid flowchart.

[`to_mermaid`][to_mermaid] turns a built graph's structure into Mermaid
flowchart source: each node kind gets a distinct shape (a step is a rectangle, a
join a hexagon, a decision a rhombus, a pause a parallelogram, and the start and
end are circles), map edges are labelled, and nodes are emitted in breadth-first
order from the start so the output is stable. The text is returned for the
caller to render; nothing is drawn or fetched.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Literal

from openfactcheck.graph.step import EdgeKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from openfactcheck.graph.graph import GraphSpec

type Direction = Literal["TD", "LR", "RL", "BT"]
"""A Mermaid flowchart layout direction: top-down, left-right, right-left, or bottom-top."""


def to_mermaid(
    spec: GraphSpec,
    *,
    direction: Direction = "TD",
    title: str | None = None,
    highlight: Iterable[str] | None = None,
) -> str:
    """Render a graph definition as Mermaid flowchart source.

    Args:
        spec: The built graph's definition to render.
        direction: Layout direction of the flowchart.
        title: An optional title shown above the diagram.
        highlight: Node ids to draw with a highlight style.

    Returns:
        Mermaid flowchart source as a string.
    """
    order = _ordered_nodes(spec)
    highlighted = set(highlight or ())
    lines: list[str] = []
    if title is not None:
        lines += ["---", f"title: {title}", "---"]
    lines.append(f"flowchart {direction}")
    lines.extend(f"    {_render_node(spec, node_id)}" for node_id in order)
    for source_id in order:
        for edge in spec.edges_by_source.get(source_id, []):
            connector = " -->|map| " if edge.kind is EdgeKind.MAP else " --> "
            lines.append(f"    {source_id}{connector}{edge.dest_id}")
    if highlighted:
        lines.append("    classDef highlight fill:#fdff32,stroke:#333;")
        lines.extend(f"    class {node_id} highlight;" for node_id in order if node_id in highlighted)
    return "\n".join(lines)


def _ordered_nodes(spec: GraphSpec) -> list[str]:
    """Return node ids in breadth-first order from the start node."""
    order: list[str] = []
    seen = {spec.start_id}
    queue = deque([spec.start_id])
    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for edge in spec.edges_by_source.get(node_id, []):
            if edge.dest_id not in seen:
                seen.add(edge.dest_id)
                queue.append(edge.dest_id)
    return order


def _render_node(spec: GraphSpec, node_id: str) -> str:
    """Render one node id with the shape that matches its kind."""
    label = _label(node_id)
    if node_id == spec.start_id:
        return f'{node_id}(("start"))'
    if node_id == spec.end_id:
        return f'{node_id}(("end"))'
    if node_id in spec.joins:
        return f'{node_id}{{{{"{label}"}}}}'
    if node_id in spec.decisions:
        return f'{node_id}{{"{label}"}}'
    if node_id in spec.pauses:
        return f'{node_id}[/"{label}"/]'
    return f'{node_id}["{label}"]'


def _label(node_id: str) -> str:
    """Return a readable label for a node id, cleaning generated names."""
    if node_id.startswith("__"):
        return node_id.strip("_").replace("_", " ")
    return node_id
