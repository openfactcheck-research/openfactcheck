"""Tests for the all-optional partial-model builder."""

from pydantic import BaseModel, TypeAdapter

from openfactcheck.chat.partial import partial_model


class _Verdict(BaseModel):
    reasoning: str
    factuality: bool
    correction: str | None = None


def test_partial_model_makes_every_field_optional() -> None:
    """A partial variant validates an empty object, leaving every field None."""
    partial = partial_model(_Verdict)

    instance = partial.model_validate({})

    assert instance.model_dump() == {"reasoning": None, "factuality": None, "correction": None}


def test_partial_model_validates_incomplete_json_progressively() -> None:
    """Partial validation fills only the fields present so far in a half-written object."""
    adapter = TypeAdapter(partial_model(_Verdict))

    instance = adapter.validate_json(
        '{"reasoning": "Canberra is the capi',
        experimental_allow_partial="trailing-strings",
    )

    dumped = instance.model_dump()
    assert dumped["reasoning"] == "Canberra is the capi"
    assert dumped["factuality"] is None


def test_partial_model_is_cached() -> None:
    """Repeated calls for the same model return one shared variant."""
    assert partial_model(_Verdict) is partial_model(_Verdict)
