"""All-optional model variants for validating partial structured output.

Streaming structured output validates JSON that is still being written. A
model's required fields would reject a half-finished object, so each model is
mirrored into a variant whose every field is optional; partial JSON then
validates into a progressively filled instance, and the final, complete JSON is
validated against the original model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, create_model

if TYPE_CHECKING:
    from pydantic import BaseModel

_PARTIAL_MODELS: dict[type[BaseModel], type[BaseModel]] = {}
"""Cache mapping a source model to its all-optional partial variant."""


def partial_model(model: type[BaseModel]) -> type[BaseModel]:
    """Return a variant of ``model`` with every top-level field optional.

    Each field keeps its annotation but gains ``| None`` and a ``None`` default,
    so partial JSON validates into an instance carrying only the fields that have
    arrived so far, the rest left ``None``. A nested model keeps its own schema,
    so a nested object appears once enough of it has streamed to validate.

    Results are cached, so repeated calls for the same model return one shared
    variant.

    Args:
        model: The model whose fields should be made optional.

    Returns:
        A model class named ``Partial<Name>`` with every field optional.
    """
    cached = _PARTIAL_MODELS.get(model)
    if cached is not None:
        return cached
    # Field definitions are built dynamically, so their value type is Any.
    fields: dict[str, Any] = {}
    for name, info in model.model_fields.items():
        annotation = info.annotation or object
        fields[name] = (annotation | None, None)
    partial = create_model(f"Partial{model.__name__}", __config__=ConfigDict(extra="ignore"), **fields)
    _PARTIAL_MODELS[model] = partial
    return partial
