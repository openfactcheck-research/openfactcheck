"""RARR editor."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Source
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

DEFAULT_MAX_EDIT_DISTANCE = 50
"""Default cap on a single edit's character edit distance, from the paper."""

DEFAULT_MAX_EDIT_RATIO = 0.5
"""Default cap on a single edit's edit distance as a fraction of the passage length, from the paper."""


class RARREditorModel(BaseModel):
    """RARR's structured edit result.

    The editor returns the `fix` when it is within the size limits. It is also the
    value handed to a call's ``on_partial`` hook, filling in as the model writes it.
    """

    reasoning: str
    fix: str


@dataclass(frozen=True, slots=True)
class RARREditor:
    """Edit a passage to agree with a piece of evidence, following RARR's method.

    Given the passage so far, a question, and disagreeing evidence, the editor
    rewrites the passage to agree with the evidence while changing as little as
    possible. To preserve the original wording, an edit is rejected (the passage
    is left unchanged) when it changes more than the allowed number of characters
    or fraction of the passage.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "editor.md"))
    """The editing prompt. Defaults to RARR's; override to customise."""

    max_edit_distance: int = DEFAULT_MAX_EDIT_DISTANCE
    """Largest character edit distance an edit may have before it is rejected."""

    max_edit_ratio: float = DEFAULT_MAX_EDIT_RATIO
    """Largest edit distance, as a fraction of the passage length, an edit may have before it is rejected."""

    async def __call__(
        self,
        passage: str,
        question: str,
        source: Source,
        *,
        on_partial: Callable[[RARREditorModel], None] | None = None,
    ) -> str:
        """Edit ``passage`` to agree with ``source`` on the answer to ``question``.

        Args:
            passage: The passage as edited so far.
            question: The question the evidence was retrieved for.
            source: The evidence to make the passage agree with.
            on_partial: Called with the edit as it streams in. Omit it for a single
                non-streaming call. The returned text is the same either way.

        Returns:
            The edited passage when the edit is within the size limits; otherwise
            the passage unchanged.
        """
        messages = self.prompt.to_messages(claim=passage, query=question, evidence=source.content)
        result = (
            await self.client.acompletion_as(messages, RARREditorModel)
            if on_partial is None
            else await self._stream(messages, on_partial)
        )
        fix = result.fix.strip()
        if fix and self._within_limits(passage, fix):
            return fix
        return passage

    def _within_limits(self, original: str, edited: str) -> bool:
        """Whether an edit changes little enough to keep, by the paper's two caps."""
        distance = self._edit_distance(original, edited)
        return distance <= self.max_edit_distance and distance <= self.max_edit_ratio * len(original)

    @staticmethod
    def _edit_distance(left: str, right: str) -> int:
        """Return the Levenshtein edit distance between two strings."""
        if left == right:
            return 0
        previous = list(range(len(right) + 1))
        for i, left_char in enumerate(left, start=1):
            current = [i]
            for j, right_char in enumerate(right, start=1):
                cost = 0 if left_char == right_char else 1
                current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
            previous = current
        return previous[-1]

    async def _stream(self, messages: list[Message], on_partial: Callable[[RARREditorModel], None]) -> RARREditorModel:
        """Stream the edit, forwarding each partial result to ``on_partial``."""
        result: RARREditorModel | None = None
        async for partial in self.client.astream_as(messages, RARREditorModel):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("editor stream produced no value")
        return result
