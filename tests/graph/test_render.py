"""Tests for rendering a graph diagram to an image through a Mermaid server."""

import base64
import urllib.error

import pytest
from pytest_mock import MockerFixture

from openfactcheck.graph import Graph, GraphBuilder, GraphRenderError, StepContext, to_mermaid_image


def _echo_graph() -> Graph[str, str]:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def echo(ctx: StepContext[str]) -> str:
        return ctx.inputs

    g.add(
        g.edge_from(g.start_node).to(echo),
        g.edge_from(echo).to(g.end_node),
    )
    return g.build()


def _mock_urlopen(mocker: MockerFixture, data: bytes) -> MockerFixture:
    """Patch urlopen to act as a context manager whose response reads ``data``."""
    cm = mocker.MagicMock()
    cm.__enter__.return_value.read.return_value = data
    return mocker.patch("urllib.request.urlopen", return_value=cm)


def test_to_mermaid_image(mocker: MockerFixture) -> None:
    urlopen = _mock_urlopen(mocker, b"PNGDATA")

    result = to_mermaid_image("flowchart TD\n    A --> B")

    assert result == b"PNGDATA"
    encoded = base64.b64encode(b"flowchart TD\n    A --> B").decode("ascii")
    assert urlopen.call_args.args[0] == f"https://mermaid.ink/img/{encoded}"


def test_to_mermaid_image_svg_and_custom_base_url(mocker: MockerFixture) -> None:
    urlopen = _mock_urlopen(mocker, b"<svg/>")

    result = to_mermaid_image("flowchart TD", image_type="svg", base_url="http://localhost:3000")

    assert result == b"<svg/>"
    encoded = base64.b64encode(b"flowchart TD").decode("ascii")
    assert urlopen.call_args.args[0] == f"http://localhost:3000/svg/{encoded}"


def test_to_mermaid_image_raises_on_unreachable_server(mocker: MockerFixture) -> None:
    mocker.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("unreachable"))

    with pytest.raises(GraphRenderError):
        to_mermaid_image("flowchart TD")


def test_Graph_to_mermaid_image(mocker: MockerFixture) -> None:
    _mock_urlopen(mocker, b"PNGDATA")

    assert _echo_graph().to_mermaid_image() == b"PNGDATA"


def test_Graph_to_mermaid_view(mocker: MockerFixture) -> None:
    _mock_urlopen(mocker, b"PNGDATA")

    view = _echo_graph().to_mermaid_view()

    assert view._repr_png_() == b"PNGDATA"
