"""Tests for the result summary computed from a result's verdicts."""

from openfactcheck.components.types import Claim, Result, Verdict


def _verdict(label: str) -> Verdict:
    return Verdict(claim=Claim(text="c"), label=label, reasoning="r")  # type: ignore[arg-type]


def _result(*labels: str) -> Result:
    return Result(verdicts=[_verdict(label) for label in labels])


def test_Result_summary_counts() -> None:
    """The summary counts each label and the total."""
    summary = _result("supported", "refuted", "not_enough_evidence", "supported").summary

    assert summary.supported == 2
    assert summary.refuted == 1
    assert summary.not_enough_evidence == 1
    assert summary.total == 4


def test_Result_summary_factual_all_supported() -> None:
    """All supported reads as factual."""
    assert _result("supported", "supported").summary.factual is True


def test_Result_summary_factual_any_refuted() -> None:
    """Any refuted claim reads as not factual."""
    assert _result("supported", "refuted").summary.factual is False


def test_Result_summary_factual_inconclusive() -> None:
    """No refutation but insufficient evidence yields no overall judgment."""
    assert _result("supported", "not_enough_evidence").summary.factual is None


def test_Result_summary_empty() -> None:
    """A result with no verdicts cannot be judged."""
    summary = _result().summary

    assert summary.total == 0
    assert summary.factual is None


def test_Result_summary_serializes() -> None:
    """The summary is included when the result is dumped."""
    dumped = _result("supported").model_dump()

    assert dumped["summary"]["supported"] == 1
    assert dumped["summary"]["factual"] is True


def test_Result_summary_round_trips() -> None:
    """A dumped result reloads, the serialized summary being recomputed rather than read back."""
    result = _result("supported", "refuted")

    reloaded = Result.model_validate(result.model_dump())

    assert reloaded == result
    assert reloaded.summary.factual is False
