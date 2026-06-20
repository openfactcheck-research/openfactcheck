"""RARR evidence selection for the attribution report."""

from __future__ import annotations

import asyncio
import itertools
from typing import TYPE_CHECKING

from openfactcheck.components.rarr.imports import load_cross_encoder

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

    from openfactcheck.components.types import Source

DEFAULT_MAX_SELECTED = 5
"""Default cap on the number of sources in the attribution report, from the paper."""

DEFAULT_RANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
"""Default cross-encoder used to score how well a source answers a question."""


class RARREvidenceSelector:
    """Select the attribution report by maximizing question coverage, following RARR's method.

    Scores every source against every question with a cross-encoder, then picks
    the subset of at most ``max_selected`` sources that maximizes total coverage,
    where a question's coverage is the score of the best source for it. The
    cross-encoder is loaded once on first use and reused; it needs the ``rarr``
    extra (``sentence-transformers``).
    """

    def __init__(self, *, max_selected: int = DEFAULT_MAX_SELECTED, ranker_model: str = DEFAULT_RANKER_MODEL) -> None:
        """Build an evidence selector.

        Args:
            max_selected: Largest number of sources to keep in the report.
            ranker_model: Cross-encoder model id used to score sources against questions.
        """
        self._max_selected = max_selected
        self._ranker_name = ranker_model
        self._ranker: CrossEncoder | None = None

    async def __call__(self, questions: list[str], sources: list[Source]) -> list[Source]:
        """Select the sources that best cover the questions.

        Args:
            questions: All questions generated for the passage.
            sources: The candidate sources retrieved across all questions.

        Returns:
            At most ``max_selected`` sources, chosen to maximize question coverage;
            the candidates unchanged when there are no more than ``max_selected``.
        """
        unique_questions = list(dict.fromkeys(question for question in questions if question.strip()))
        unique_sources = self._dedupe(sources)
        if not unique_questions or len(unique_sources) <= self._max_selected:
            return unique_sources
        matrix = await asyncio.to_thread(self._score_matrix, unique_questions, unique_sources)
        return [unique_sources[index] for index in self._best_combination(matrix)]

    @staticmethod
    def _dedupe(sources: list[Source]) -> list[Source]:
        """Drop sources with duplicate content, keeping the first of each."""
        by_content: dict[str, Source] = {}
        for source in sources:
            by_content.setdefault(source.content, source)
        return list(by_content.values())

    def _score_matrix(self, questions: list[str], sources: list[Source]) -> list[list[float]]:
        """Score every source against every question, one row per question."""
        ranker = self._load_ranker()
        return [
            [float(score) for score in ranker.predict([(question, source.content) for source in sources])]
            for question in questions
        ]

    def _best_combination(self, matrix: list[list[float]]) -> tuple[int, ...]:
        """Return the source indices maximizing total question coverage."""
        num_sources = len(matrix[0])
        best_combination: tuple[int, ...] = ()
        best_value = float("-inf")
        for combination in itertools.combinations(range(num_sources), self._max_selected):
            value = sum(max(row[index] for index in combination) for row in matrix)
            if value > best_value:
                best_value = value
                best_combination = combination
        return best_combination

    def _load_ranker(self) -> CrossEncoder:
        """Build the cross-encoder once and reuse it across calls."""
        if self._ranker is None:
            self._ranker = load_cross_encoder()(self._ranker_name, max_length=512)
        return self._ranker
