"""Placeholder substitution for prompt templates.

Templates reference variables with ``{{name}}``; whitespace inside the braces
is ignored.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


_TOKEN_RE = re.compile(
    r"""
      \\\{\\\{                                          # escaped opening: \{\{
    | \\\}\\\}                                          # escaped closing: \}\}
    | \{\{\s*(?P<name>[A-Za-z_][A-Za-z_0-9]*)\s*\}\}    # placeholder
    """,
    re.VERBOSE,
)
"""Single-pass scanner matching either an escape pair or a placeholder.

Escape markers come first in the alternation so an escaped sequence never
matches the placeholder branch.
"""


def find_placeholders(template: str) -> set[str]:
    """Return the placeholder names referenced in ``template``.

    Args:
        template: Raw template text.

    Returns:
        The set of placeholder identifiers referenced in the template.
    """
    return {m.group("name") for m in _TOKEN_RE.finditer(template) if m.group("name")}


def substitute(template: str, values: Mapping[str, object]) -> str:
    """Substitute every ``{{name}}`` reference in ``template``.

    Args:
        template: Raw template text.
        values: Mapping from placeholder name to substitution value. Values
            are stringified.

    Returns:
        The template with every placeholder substituted.

    Raises:
        KeyError: A placeholder name does not appear in ``values``. Callers
            wrap this as [`PromptVariableError`][PromptVariableError].
    """

    def _replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name is not None:
            return str(values[name])
        escaped = match.group(0)
        return "{{" if escaped == r"\{\{" else "}}"

    return _TOKEN_RE.sub(_replace, template)
