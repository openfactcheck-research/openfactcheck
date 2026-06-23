"""Render a graph definition as a Mermaid flowchart, and that flowchart as an image.

[`to_mermaid`][to_mermaid] turns a built graph's structure into Mermaid
flowchart source: each node kind gets a distinct shape (a step is a rectangle, a
join a hexagon, a decision a rhombus, a pause a parallelogram, and the start and
end are filled circles). Fan-out (map) edges are drawn thick, decision branches
dotted, and an edge entering a join is labeled with that join's fold operation
(collect or reduce). A join declared inline on the edge itself has no node of
its own and renders as that label on a single edge to its successor. So the
diagram shows where the graph forks, routes, and rejoins; nodes are emitted in
breadth-first order from the start so the output is stable. With ``show_types``,
each edge is also labeled with the data it carries, read from the source node's
declared output type. With ``expand_subgraphs``, a subgraph node is drawn as a
nested cluster of its inner nodes, with edges wired to the inner nodes its flow
enters and leaves, rather than a single box.

[`to_mermaid_image`][to_mermaid_image] takes that source and renders it to image
bytes through a Mermaid server (mermaid.ink by default); the default server
encodes the diagram into the request URL, so a very large graph may need a
self-hosted server supplied as ``base_url``.
"""

from __future__ import annotations

import base64
import urllib.parse
from collections import deque
from dataclasses import dataclass, field
from types import UnionType
from typing import TYPE_CHECKING, Literal, Union, get_args, get_origin

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


@dataclass(frozen=True, slots=True)
class _Crossing:
    """An expanded subgraph's prefixed inner ids: where edges enter and leave, and all inner nodes for ranking."""

    entries: list[str]
    exits: list[str]
    inner: list[str]


@dataclass(frozen=True, slots=True)
class _Level:
    """The per-spec rendering context: inline joins, the id prefix, and each expanded subgraph's crossing."""

    inline: frozenset[str]
    prefix: str
    crossings: dict[str, _Crossing]


@dataclass(slots=True)
class _Doc:
    """The accumulating flowchart: its lines plus the ids that take the boundary and highlight styles."""

    expand: bool
    show_types: bool
    highlighted: frozenset[str]
    lines: list[str] = field(default_factory=list[str])
    boundary: list[str] = field(default_factory=list[str])
    marked: list[str] = field(default_factory=list[str])


def to_mermaid(  # noqa: PLR0913 - public renderer; each argument is a distinct display option
    spec: GraphSpec,
    *,
    direction: Direction = "TD",
    title: str | None = None,
    highlight: Iterable[str] | None = None,
    show_types: bool = False,
    expand_subgraphs: bool = False,
) -> str:
    """Render a graph definition as Mermaid flowchart source.

    Args:
        spec: The built graph's definition to render.
        direction: Layout direction of the flowchart.
        title: An optional title shown above the diagram.
        highlight: Node ids to draw with a highlight style.
        show_types: Label each edge with the type of data it carries, read from
            the source node's declared output type (the graph input type for the
            start edge); a fan-in collect is labeled with the gathered list type.
        expand_subgraphs: Draw each subgraph node as a nested cluster of its inner
            nodes, wiring edges to the inner nodes its flow enters and leaves,
            rather than a single opaque node.

    Returns:
        Mermaid flowchart source as a string.
    """
    doc = _Doc(expand=expand_subgraphs, show_types=show_types, highlighted=frozenset(highlight or ()))
    if title is not None:
        doc.lines += ["---", f"title: {title}", "---"]
    doc.lines.append(f"flowchart {direction}")
    _emit(doc, spec, prefix="", root=True)
    doc.lines.append("    classDef boundary fill:#005355,stroke:#005355,color:#ffffff;")
    doc.lines.append(f"    class {','.join(doc.boundary)} boundary;")
    if doc.marked:
        doc.lines.append("    classDef highlight fill:#fdff32,stroke:#333;")
        doc.lines.extend(f"    class {rendered_id} highlight;" for rendered_id in doc.marked)
    return "\n".join(doc.lines)


def _emit(doc: _Doc, spec: GraphSpec, *, prefix: str, root: bool) -> None:
    """Append ``spec``'s nodes and edges to ``doc``, expanding subgraph nodes into clusters when asked.

    Node ids carry ``prefix`` so a nested spec stays unique in the flowchart's shared id space, while the
    label keeps each node's own id. An expanded subgraph hides its own start and end: an edge into it attaches
    to the inner node its flow enters and an edge out leaves from the inner node it exits, with an invisible
    link pinning the successor below the cluster. ``root`` is true only for the outermost graph, whose start
    and end are the ones drawn.
    """
    inline = frozenset(join_id for join_id, join in spec.joins.items() if join.inline)
    order = [node_id for node_id in _ordered_nodes(spec) if node_id not in inline]
    subgraphs = spec.subgraphs if doc.expand else {}
    crossings: dict[str, _Crossing] = {}
    for node_id in order:
        rendered_id = f"{prefix}{node_id}"
        if node_id in (spec.start_id, spec.end_id):
            if root:
                doc.boundary.append(rendered_id)
                doc.lines.append(f"    {_render_node(spec, node_id, prefix)}")
            continue
        if node_id in doc.highlighted:
            doc.marked.append(rendered_id)
        if node_id in subgraphs:
            doc.lines.append(f'    subgraph {rendered_id}["{_label(node_id)}"]')
            _emit(doc, subgraphs[node_id], prefix=f"{rendered_id}/", root=False)
            doc.lines.append("    end")
            crossings[rendered_id] = _crossing(subgraphs[node_id], f"{rendered_id}/")
        else:
            doc.lines.append(f"    {_render_node(spec, node_id, prefix)}")
    level = _Level(inline=inline, prefix=prefix, crossings=crossings)
    for source_id in order:
        for edge in spec.edges_by_source.get(source_id, []):
            if not root and (edge.source_id == spec.start_id or edge.dest_id == spec.end_id):
                continue
            doc.lines.extend(
                f"    {rendered}" for rendered in _render_edge(spec, edge, level, show_types=doc.show_types)
            )


def _crossing(spec: GraphSpec, prefix: str) -> _Crossing:
    """Find an expanded subgraph's entry, exit, and inner node ids, prefixed, for wiring edges and ranking."""
    inline = {join_id for join_id, join in spec.joins.items() if join.inline}
    entries = [f"{prefix}{edge.dest_id}" for edge in spec.edges_by_source.get(spec.start_id, [])]
    exits = [
        f"{prefix}{edge.source_id}"
        for edges in spec.edges_by_source.values()
        for edge in edges
        if edge.dest_id == spec.end_id
    ]
    inner = [
        f"{prefix}{node_id}"
        for node_id in _ordered_nodes(spec)
        if node_id not in (spec.start_id, spec.end_id) and node_id not in inline
    ]
    return _Crossing(entries=entries, exits=exits, inner=inner)


def _render_edge(spec: GraphSpec, edge: Edge, level: _Level, *, show_types: bool) -> list[str]:
    """Render an edge to one or more flowchart edges, collapsing inline joins and crossing subgraph clusters.

    An inline join has no node of its own, so an edge entering one is drawn straight through to its successor.
    An edge entering an expanded subgraph attaches to the inner node its flow enters, and an edge leaving one
    starts from the inner node it exits; an invisible link then pins the successor below the cluster, since the
    exit node may sit above the cluster's deepest node. With ``show_types`` the label also carries the data
    type crossing the edge; the type lookup uses the node's own id.
    """
    if edge.dest_id in level.inline:
        dest_id, verb, arrow = spec.edges_by_source[edge.dest_id][0].dest_id, spec.joins[edge.dest_id].verb, "-->"
    elif edge.kind is EdgeKind.MAP:
        dest_id, verb, arrow = edge.dest_id, "map", "==>"
    elif (dest_join := spec.joins.get(edge.dest_id)) is not None:
        dest_id, verb, arrow = edge.dest_id, dest_join.verb, "-->"
    elif edge.source_id in spec.decisions:
        dest_id, verb, arrow = edge.dest_id, None, "-.->"
    else:
        dest_id, verb, arrow = edge.dest_id, None, "-->"
    label = _edge_label(spec, edge.source_id, verb, show_types=show_types)
    connector = f"{arrow}|{label}|" if label else arrow
    src = level.crossings.get(f"{level.prefix}{edge.source_id}")
    dst = level.crossings.get(f"{level.prefix}{dest_id}")
    sources = src.exits if src is not None else [f"{level.prefix}{edge.source_id}"]
    dests = dst.entries if dst is not None else [f"{level.prefix}{dest_id}"]
    rendered = [f"{source} {connector} {dest}" for source in sources for dest in dests]
    if src is not None:
        deep = [node for node in src.inner if node not in src.exits and node not in src.entries]
        rendered.extend(f"{node} ~~~ {dest}" for node in deep for dest in dests)
    return rendered


def _edge_label(spec: GraphSpec, source_id: str, verb: str | None, *, show_types: bool) -> str:
    """Build an edge label: the fold verb alone, or the verb plus the carried type when show_types is set."""
    if not show_types:
        return verb or ""
    carried = _carried_type(spec, source_id, verb)
    if verb and carried:
        return f'"{verb}: {carried}"'
    if carried:
        return f'"{carried}"'
    return f'"{verb}"' if verb else ""


def _carried_type(spec: GraphSpec, source_id: str, verb: str | None) -> str | None:
    """Format the type an edge carries: the source's output, wrapped in a list for a collect fan-in."""
    emitted = spec.input_type if source_id == spec.start_id else _step_output(spec, source_id)
    if emitted is None:
        return None
    formatted = _format_type(emitted)
    return f"list[{formatted}]" if verb == "collect" else formatted


def _step_output(spec: GraphSpec, source_id: str) -> object | None:
    """Return a step node's declared output type, or ``None`` for the start node or a non-step source."""
    step = spec.steps.get(source_id)
    return step.output_type if step is not None else None


def _format_type(annotation: object) -> str:
    """Format a type annotation as a short label: drop module paths, render generics and unions."""
    if annotation is None or annotation is type(None):
        return "None"
    origin = get_origin(annotation)
    if origin is None:
        return getattr(annotation, "__name__", None) or str(annotation).removeprefix("typing.")
    args = ", ".join(_format_type(arg) for arg in get_args(annotation))
    if origin in (Union, UnionType):
        return " | ".join(_format_type(arg) for arg in get_args(annotation))
    name = getattr(origin, "__name__", None) or str(origin)
    return f"{name}[{args}]" if args else name


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


def _render_node(spec: GraphSpec, node_id: str, prefix: str = "") -> str:
    """Render one node id with the shape that matches its kind, namespacing the id with ``prefix``."""
    label = _label(node_id)
    rendered_id = f"{prefix}{node_id}"
    if node_id == spec.start_id:
        return f'{rendered_id}(("start"))'
    if node_id == spec.end_id:
        return f'{rendered_id}(("end"))'
    if node_id in spec.joins:
        return f'{rendered_id}{{{{"{label}"}}}}'
    if node_id in spec.decisions:
        return f'{rendered_id}{{"{label}"}}'
    if node_id in spec.pauses:
        return f'{rendered_id}[/"{label}"/]'
    return f'{rendered_id}["{label}"]'


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
