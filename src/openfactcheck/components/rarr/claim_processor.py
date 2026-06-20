"""RARR claim processor."""

from collections.abc import Callable
from dataclasses import dataclass

from openfactcheck.components.types import Claim, Input


@dataclass(frozen=True, slots=True)
class RARRClaimProcessor:
    """Treat the whole input as a single claim, following RARR's method.

    RARR researches and revises a passage as a whole rather than decomposing it
    into atomic claims, so this returns the input verbatim as one claim.
    """

    async def __call__(self, text: Input, *, on_partial: Callable[[object], None] | None = None) -> list[Claim]:
        """Wrap ``text`` as a single claim.

        Args:
            text: Input text to treat as one claim.
            on_partial: Unused; this step does no streaming work.

        Returns:
            A one-element list holding the whole input as a single claim.
        """
        return [Claim(text=text.content)]
