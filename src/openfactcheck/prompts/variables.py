"""Role and variable declarations for prompt templates.

``Role`` is the role a template message can take. ``VariableSpec`` declares
one input variable's contract (name, type, required, default). A template
stores its variables as a mapping keyed by name; the spec carries its own
name so [`VariableSpec.string`][VariableSpec.string] reads naturally.

Example:
    ```python
    from openfactcheck.prompts import VariableSpec

    claim = VariableSpec.string("claim")  # required
    tone = VariableSpec.string("tone", required=False, default="neutral")  # optional
    ```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant"]
"""Role a [`PromptTemplate`][PromptTemplate] message can take.

These are the roles a template authors directly, and the roles the
``(role, text)`` tuple shorthand accepts. The chat layer's
[`Message`][openfactcheck.messages.Message] union covers additional roles
(such as tool results) that belong to a conversation rather than a template.
"""


@dataclass(frozen=True, slots=True)
class VariableSpec:
    """Declaration of one templated variable.

    Frozen dataclass; values are immutable after construction. Users
    typically build these with [`VariableSpec.string`][VariableSpec.string]
    rather than the primary constructor. Future type factories
    (``VariableSpec.integer``, ``VariableSpec.boolean``) will land
    alongside their corresponding ``type`` values; the current v1 surface
    is deliberately string-only.
    """

    name: str
    """Variable name. Must be a valid Python identifier, matching the
    ``{{name}}`` placeholder syntax. The template keys its variables by name,
    so duplicates cannot occur."""

    type: Literal["string"] = "string"
    """Value type. Only ``"string"`` is supported today."""

    required: bool = True
    """Whether the variable must appear in the values passed to
    [`PromptTemplate.to_prompt`][PromptTemplate.to_prompt]. An optional
    variable may be omitted; when it is, its
    [`default`][VariableSpec.default] is substituted instead of raising
    [`PromptVariableError`][PromptVariableError]."""

    default: str = ""
    """Value substituted when an optional variable is omitted while filling.

    Applies only to optional variables; a required variable must be
    supplied, so its default is never used."""

    @classmethod
    def string(cls, name: str, *, required: bool = True, default: str = "") -> VariableSpec:
        """Declare a string-valued variable.

        Args:
            name: Variable name; must be a valid Python identifier.
            required: Whether the values passed when filling must include this
                name. Defaults to ``True``.
            default: Value substituted when an optional variable is omitted.
                Ignored for required variables.

        Returns:
            A ``VariableSpec`` with ``type="string"``.
        """
        return cls(name=name, type="string", required=required, default=default)
