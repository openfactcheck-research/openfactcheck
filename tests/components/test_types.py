"""Tests for the report summary computed from a report's verdicts."""

from openfactcheck.components.types import Claim, Input, Report, Verdict


def _verdict(label: str) -> Verdict:
    return Verdict(claim=Claim(text="c"), label=label, reasoning="r")  # type: ignore[arg-type]


def _report(*labels: str) -> Report:
    return Report(input=Input(content="x"), verdicts=[_verdict(label) for label in labels])


def test_Report_summary_counts() -> None:
    """The summary counts each label and the total."""
    summary = _report("supported", "refuted", "not_enough_evidence", "supported").summary

    assert summary.supported == 2
    assert summary.refuted == 1
    assert summary.not_enough_evidence == 1
    assert summary.total == 4


def test_Report_summary_factual_all_supported() -> None:
    """All supported reads as factual."""
    assert _report("supported", "supported").summary.factual is True


def test_Report_summary_factual_any_refuted() -> None:
    """Any refuted claim reads as not factual."""
    assert _report("supported", "refuted").summary.factual is False


def test_Report_summary_factual_inconclusive() -> None:
    """No refutation but insufficient evidence yields no overall judgment."""
    assert _report("supported", "not_enough_evidence").summary.factual is None


def test_Report_summary_empty() -> None:
    """A report with no verdicts cannot be judged."""
    summary = _report().summary

    assert summary.total == 0
    assert summary.factual is None


def test_Report_summary_serializes() -> None:
    """The summary is included when the report is dumped."""
    dumped = _report("supported").model_dump()

    assert dumped["summary"]["supported"] == 1
    assert dumped["summary"]["factual"] is True


def test_Report_summary_round_trips() -> None:
    """A dumped report reloads, the serialized summary being recomputed rather than read back."""
    report = _report("supported", "refuted")

    reloaded = Report.model_validate(report.model_dump())

    assert reloaded == report
    assert reloaded.summary.factual is False
