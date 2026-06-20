"""Dummy claim processor."""

from collections.abc import Callable
from dataclasses import dataclass

from openfactcheck.components.types import Claim, Input


@dataclass(frozen=True, slots=True)
class DummyClaimProcessor:
    """Claim processor that performs no extraction.

    Wraps the whole input as a single claim, or yields nothing when the input is
    blank.
    """

    async def __call__(
        self,
        text: Input,
        *,
        on_partial: Callable[[object], None] | None = None,
    ) -> list[Claim]:
        """Wrap ``text`` as a single claim.

        Args:
            text: Input to turn into claims.
            on_partial: Ignored; this component produces its result in one step.

        Returns:
            One claim holding the full input content, or an empty list when the
            content is blank.
        """
        if not text.content.strip():
            return []
        return [Claim(text=text.content)]
