"""Render a graph definition as a Mermaid flowchart, and that flowchart as an image.

[`to_mermaid`][to_mermaid] turns a built graph's structure into Mermaid
flowchart source: each node kind gets a distinct shape (a step is a rectangle, a
join a hexagon, a decision a rhombus, a pause a parallelogram, and the start and
end are filled circles). Fan-out (map) edges are drawn thick and decision
branches dotted, so the diagram shows where the graph forks and routes; nodes
are emitted in breadth-first order from the start so the output is stable.

[`to_mermaid_image`][to_mermaid_image] takes that source and renders it to image
bytes through a Mermaid server (mermaid.ink by default); the default server
encodes the diagram into the request URL, so a very large graph may need a
self-hosted server supplied as ``base_url``.
"""

from __future__ import annotations

import base64
import urllib.parse
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import httpx

from openfactcheck.graph.errors import GraphRenderError
from openfactcheck.graph.step import EdgeKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from openfactcheck.graph.graph import GraphSpec
    from openfactcheck.graph.step import Edge

type Direction = Literal["TD", "LR", "RL", "BT"]
"""A Mermaid flowchart layout direction: top-down, left-right, right-left, or bottom-top."""

type ImageType = Literal["png", "svg"]
"""The image format a Mermaid server renders: a PNG raster or an SVG vector."""


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
            lines.append(f"    {source_id}{_connector(spec, edge)}{edge.dest_id}")
    lines.append("    classDef boundary fill:#005355,stroke:#005355,color:#ffffff;")
    lines.append(f"    class {spec.start_id},{spec.end_id} boundary;")
    if highlighted:
        lines.append("    classDef highlight fill:#fdff32,stroke:#333;")
        lines.extend(f"    class {node_id} highlight;" for node_id in order if node_id in highlighted)
    return "\n".join(lines)


def _connector(spec: GraphSpec, edge: Edge) -> str:
    """Return the arrow for an edge: thick for map fan-out, dotted for a decision branch."""
    if edge.kind is EdgeKind.MAP:
        return " ==>|map| "
    if edge.source_id in spec.decisions:
        return " -.-> "
    return " --> "


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


_IMAGE_PATHS: dict[ImageType, str] = {"png": "img", "svg": "svg"}
"""The mermaid.ink path segment that serves each image type."""


def to_mermaid_image(
    source: str,
    *,
    base_url: str = "https://mermaid.ink",
    image_type: ImageType = "png",
    timeout: float = 30.0,
) -> bytes:
    """Render Mermaid source to image bytes through a Mermaid server.

    The diagram is encoded into the request URL, so a very large graph can
    exceed the server's URL length limit; point ``base_url`` at a self-hosted
    server when that happens.

    Args:
        source: Mermaid diagram source, as returned by [`to_mermaid`][to_mermaid].
        base_url: Base URL of the Mermaid rendering server.
        image_type: Image format to request.
        timeout: Seconds to wait for the server before giving up.

    Returns:
        The rendered image's raw bytes.

    Raises:
        GraphRenderError: If ``base_url`` is not an http or https URL, or the
            server cannot be reached or returns an error, including when the
            diagram exceeds the request's limits.
    """
    if urllib.parse.urlsplit(base_url).scheme not in {"http", "https"}:
        raise GraphRenderError(f"base_url must be an http or https URL, got {base_url!r}")
    encoded = base64.urlsafe_b64encode(source.encode()).decode("ascii")
    url = f"{base_url}/{_IMAGE_PATHS[image_type]}/{encoded}"
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GraphRenderError(f"could not render diagram via {base_url}: {exc}") from exc
    return response.content


@dataclass(frozen=True, slots=True)
class _MermaidView:  # pyright: ignore[reportUnusedClass] - used by Graph.to_mermaid_view across the module boundary.
    """A rendered diagram that displays inline in a notebook."""

    png: bytes
    """The rendered PNG image bytes."""

    def _repr_png_(self) -> bytes:
        """Return the PNG bytes a notebook displays for this object."""
        return self.png
