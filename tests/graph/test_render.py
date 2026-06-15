"""Tests for rendering a graph diagram to an image through a Mermaid server."""

import base64

import httpx
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


def _mock_httpx_get(mocker: MockerFixture, data: bytes) -> MockerFixture:
    """Patch httpx.get to return a response whose content is ``data``."""
    response = mocker.MagicMock()
    response.content = data
    return mocker.patch("httpx.get", return_value=response)


def test_to_mermaid_image(mocker: MockerFixture) -> None:
    get = _mock_httpx_get(mocker, b"PNGDATA")

    result = to_mermaid_image("flowchart TD\n    A --> B")

    assert result == b"PNGDATA"
    encoded = base64.b64encode(b"flowchart TD\n    A --> B").decode("ascii")
    assert get.call_args.args[0] == f"https://mermaid.ink/img/{encoded}"


def test_to_mermaid_image_svg_and_custom_base_url(mocker: MockerFixture) -> None:
    get = _mock_httpx_get(mocker, b"<svg/>")

    result = to_mermaid_image("flowchart TD", image_type="svg", base_url="http://localhost:3000")

    assert result == b"<svg/>"
    encoded = base64.b64encode(b"flowchart TD").decode("ascii")
    assert get.call_args.args[0] == f"http://localhost:3000/svg/{encoded}"


def test_to_mermaid_image_raises_on_unreachable_server(mocker: MockerFixture) -> None:
    mocker.patch("httpx.get", side_effect=httpx.ConnectError("unreachable"))

    with pytest.raises(GraphRenderError):
        to_mermaid_image("flowchart TD")


def test_to_mermaid_image_raises_on_non_http_base_url() -> None:
    with pytest.raises(GraphRenderError):
        to_mermaid_image("flowchart TD", base_url="file:///etc/passwd")


def test_Graph_to_mermaid_image(mocker: MockerFixture) -> None:
    _mock_httpx_get(mocker, b"PNGDATA")

    assert _echo_graph().to_mermaid_image() == b"PNGDATA"


def test_Graph_to_mermaid_view(mocker: MockerFixture) -> None:
    _mock_httpx_get(mocker, b"PNGDATA")

    view = _echo_graph().to_mermaid_view()

    assert view._repr_png_() == b"PNGDATA"
