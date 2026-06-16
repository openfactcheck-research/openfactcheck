"""The prompts -> chat seam: a filled template's messages feed ChatClient."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat import ChatClient, OpenAIConfig
from openfactcheck.chat.responses import ChatResponse
from openfactcheck.messages import AssistantMessage
from openfactcheck.prompts import PromptTemplate

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from openfactcheck.chat.requests import ChatRequest
    from openfactcheck.chat.responses import StreamEvent


class _RecordingBackend:
    """Backend stub that records the request and returns a fixed response."""

    def __init__(self) -> None:
        self.request: ChatRequest | None = None

    def completion(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        return ChatResponse(message=AssistantMessage(content="ok"), model="m", provider="openai")

    async def acompletion(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError

    def stream(self, request: ChatRequest) -> Iterator[StreamEvent]:
        raise NotImplementedError

    def astream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError


def test_PromptTemplate_to_messages_feeds_chat_client() -> None:
    """A filled template's messages pass straight into ChatClient.completion."""
    backend = _RecordingBackend()
    client = ChatClient(config=OpenAIConfig(model="gpt-4o"), backend=backend)
    template = PromptTemplate.from_messages(
        [("system", "S"), ("user", "Claim: {{claim}}")],
        name="verifier",
    )

    client.completion(template.to_messages(claim="X"))

    assert backend.request is not None
    assert [m.content for m in backend.request.messages] == ["S", "Claim: X"]
