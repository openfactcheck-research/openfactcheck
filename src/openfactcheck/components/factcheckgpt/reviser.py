"""FactcheckGPT reviser."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Input, Verdict
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class Revision(BaseModel):
    """FactcheckGPT's structured response-revision result.

    The reviser returns the [`revised`][openfactcheck.components.factcheckgpt.Revision.revised]
    text. It is also the value handed to a call's ``on_partial`` hook, the text
    filling in as the model writes it.
    """

    revised: str


@dataclass(frozen=True, slots=True)
class FactcheckGPTReviser:
    """Rewrite the input to correct its factual errors, following FactcheckGPT's method.

    Builds the list of factually true claims from the verdicts (each claim's
    correction when it has one, otherwise the claim itself) and rewrites the
    original text against that list, preserving its wording and style.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "reviser.md"))
    """The revision prompt. Defaults to FactcheckGPT's; override to customise."""

    async def __call__(
        self,
        text: Input,
        verdicts: list[Verdict],
        *,
        on_partial: Callable[[Revision], None] | None = None,
    ) -> str:
        """Rewrite ``text`` to fix the errors recorded in ``verdicts``.

        Args:
            text: The original input that was checked.
            verdicts: Per-claim verdicts, carrying the corrections to apply.
            on_partial: Called with the revision as it streams in, each call
                carrying more of the rewritten text. Omit it for a single
                non-streaming call. The returned text is the same either way.

        Returns:
            The input rewritten so its claims read as factually correct.
        """
        messages = self.prompt.to_messages(response=text.content, claims=self._true_claims(verdicts))
        result = (
            await self.client.acompletion_as(messages, Revision)
            if on_partial is None
            else await self._stream(messages, on_partial)
        )
        return result.revised

    @staticmethod
    def _true_claims(verdicts: list[Verdict]) -> str:
        """List each claim in its corrected form, one per line, for the prompt."""
        return "\n".join(f"- {verdict.correction or verdict.claim.text}" for verdict in verdicts)

    async def _stream(self, messages: list[Message], on_partial: Callable[[Revision], None]) -> Revision:
        """Stream the revision, forwarding each partial result to ``on_partial``."""
        result: Revision | None = None
        async for partial in self.client.astream_as(messages, Revision):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("reviser stream produced no value")
        return result
