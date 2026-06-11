"""YAML frontmatter parsing for the markdown codec.

Splits the leading ``---`` block from the body and parses it into the
template's name, version, description, and variable contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, cast

import yaml

from openfactcheck.prompts.errors import PromptFormatError
from openfactcheck.prompts.variables import VariableSpec

if TYPE_CHECKING:
    from pathlib import Path

FRONTMATTER_DELIMITER: Final = "---"
"""Literal line that opens and closes the YAML frontmatter block."""

ALLOWED_FRONTMATTER_KEYS: Final[frozenset[str]] = frozenset(
    {"name", "version", "description", "variables"},
)
"""Frontmatter keys this codec recognizes. Any other key is rejected."""

ALLOWED_VARIABLE_KEYS: Final[frozenset[str]] = frozenset({"type", "required"})
"""Keys allowed inside a ``variables`` mapping entry."""

ALLOWED_VARIABLE_TYPES: Final[frozenset[str]] = frozenset({"string"})
"""Variable types supported in v1."""

_IDENTIFIER_RE: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(slots=True)
class FrontMatterParser:
    """Splits and parses a markdown prompt's YAML frontmatter.

    Holds the error-context ``path`` so [`split`][FrontMatterParser.split],
    [`parse`][FrontMatterParser.parse], and the per-field extractors share it
    without threading it through.
    """

    path: Path | None

    def split(self, text: str) -> tuple[list[str], list[str], int]:
        """Split ``text`` into (frontmatter_lines, body_lines, body_start_line)."""
        lines = text.splitlines()
        if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
            raise PromptFormatError(
                path=self.path,
                line=1,
                reason="source must begin with YAML frontmatter delimiter",
                expected=FRONTMATTER_DELIMITER,
                got=lines[0] if lines else "(empty source)",
            )

        for idx in range(1, len(lines)):
            if lines[idx].strip() == FRONTMATTER_DELIMITER:
                return lines[1:idx], lines[idx + 1 :], idx + 2

        raise PromptFormatError(
            path=self.path,
            line=None,
            reason="YAML frontmatter is not closed",
            expected=f"{FRONTMATTER_DELIMITER} on a line by itself",
            got="end of source",
        )

    def parse(self, frontmatter_text: str) -> tuple[str, int | None, str | None, dict[str, VariableSpec]]:
        """Parse YAML frontmatter into (name, version, description, variables)."""
        try:
            raw: object = yaml.safe_load(frontmatter_text) if frontmatter_text.strip() else None
        except yaml.YAMLError as exc:
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="frontmatter is not valid YAML",
                expected="a YAML mapping",
                got=str(exc),
            ) from exc

        if not isinstance(raw, dict):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="frontmatter must be a YAML mapping",
                expected="mapping with 'name' and optional fields",
                got=type(raw).__name__,
            )

        data = cast("dict[str, Any]", raw)
        if unknown := sorted(set(data) - ALLOWED_FRONTMATTER_KEYS):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="frontmatter contains unknown key",
                expected=f"one of {sorted(ALLOWED_FRONTMATTER_KEYS)}",
                got=unknown[0],
            )

        return (
            self._extract_name(data),
            self._extract_version(data),
            self._extract_description(data),
            self._extract_variables(data),
        )

    def _extract_name(self, data: dict[str, Any]) -> str:
        """Extract and validate the required frontmatter ``name``."""
        if "name" not in data:
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="frontmatter is missing required 'name'",
                expected="name: <identifier>",
                got="(no 'name' key)",
            )
        value = data["name"]
        if not isinstance(value, str) or not _IDENTIFIER_RE.match(value):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="frontmatter 'name' must be a valid identifier",
                expected="[A-Za-z_][A-Za-z0-9_]*",
                got=repr(value),
            )
        return value

    def _extract_version(self, data: dict[str, Any]) -> int | None:
        """Extract the optional integer frontmatter ``version``."""
        if "version" not in data:
            return None
        value = data["version"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="frontmatter 'version' must be an integer",
                expected="integer",
                got=type(value).__name__,
            )
        return value

    def _extract_description(self, data: dict[str, Any]) -> str | None:
        """Extract the optional frontmatter ``description``."""
        if "description" not in data:
            return None
        value = data["description"]
        if not isinstance(value, str):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="frontmatter 'description' must be a string",
                expected="string",
                got=type(value).__name__,
            )
        return value

    def _extract_variables(self, data: dict[str, Any]) -> dict[str, VariableSpec]:
        """Extract the optional frontmatter ``variables`` mapping into specs."""
        if "variables" not in data:
            return {}
        raw = data["variables"]
        if not isinstance(raw, dict):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="frontmatter 'variables' must be a mapping",
                expected="mapping of variable name to spec",
                got=type(raw).__name__,
            )
        variables = cast("dict[object, object]", raw)

        out: dict[str, VariableSpec] = {}
        for name, entry in variables.items():
            if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
                raise PromptFormatError(
                    path=self.path,
                    line=None,
                    reason="variable name must be a valid identifier",
                    expected="[A-Za-z_][A-Za-z0-9_]*",
                    got=repr(name),
                )
            out[name] = self._parse_variable_entry(name, entry)
        return out

    def _parse_variable_entry(
        self,
        name: str,
        entry: Any,  # noqa: ANN401 - entry shape validated below.
    ) -> VariableSpec:
        """Parse one frontmatter variable entry into a [`VariableSpec`][VariableSpec]."""
        if entry is None:
            return VariableSpec.string(name)
        if not isinstance(entry, dict):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason=f"variable {name!r} must be a mapping or null",
                expected="mapping with optional 'type' and 'required'",
                got=type(entry).__name__,
            )
        spec = cast("dict[str, Any]", entry)
        if unknown := sorted(set(spec) - ALLOWED_VARIABLE_KEYS):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason=f"variable {name!r} has unknown key",
                expected=f"one of {sorted(ALLOWED_VARIABLE_KEYS)}",
                got=unknown[0],
            )
        type_ = spec.get("type", "string")
        if type_ not in ALLOWED_VARIABLE_TYPES:
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason=f"variable {name!r} has unsupported type",
                expected=f"one of {sorted(ALLOWED_VARIABLE_TYPES)}",
                got=str(type_),
            )
        required = spec.get("required", True)
        if not isinstance(required, bool):
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason=f"variable {name!r} 'required' must be boolean",
                expected="true or false",
                got=type(required).__name__,
            )
        return VariableSpec(name=name, type=type_, required=required)
