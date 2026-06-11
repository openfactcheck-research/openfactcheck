"""Role-tagged body parsing for the markdown codec.

Walks the body line by line, collecting ``<system>`` / ``<user>`` /
``<assistant>`` blocks into ``(role, content)`` pairs and verifying each
block's required H1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, cast

from openfactcheck.prompts.codecs.markdown._constants import ROLE_H1
from openfactcheck.prompts.errors import PromptFormatError
from openfactcheck.prompts.variables import Role

if TYPE_CHECKING:
    from pathlib import Path

_OPEN_RE: Final = re.compile(r"^<(system|user|assistant)>\s*$")
_CLOSE_RE: Final = re.compile(r"^</(system|user|assistant)>\s*$")


@dataclass(slots=True)
class BodyParser:
    """Parses the role-tagged body of a markdown prompt.

    [`parse`][BodyParser.parse] drives a line-by-line state machine, opening a
    block on an opening tag, closing it on a closing tag, and otherwise
    collecting content lines. A parser instance is single-use.
    """

    path: Path | None
    role: Role | None = None
    role_start: int | None = None
    body: list[str] = field(default_factory=list[str])
    blocks: list[tuple[Role, str]] = field(default_factory=list[tuple[Role, str]])
    seen: set[Role] = field(default_factory=set[Role])

    def parse(self, body_lines: list[str], *, body_start_line: int) -> tuple[tuple[Role, str], ...]:
        """Parse role-tagged body lines into ``(role, content)`` pairs."""
        for offset, line in enumerate(body_lines):
            file_line = body_start_line + offset
            if open_match := _OPEN_RE.match(line):
                self._open_block(cast("Role", open_match.group(1)), file_line)
            elif close_match := _CLOSE_RE.match(line):
                self._close_block(cast("Role", close_match.group(1)), file_line)
            else:
                self._add_line(line)
        return self._finish()

    def _open_block(self, role: Role, line: int) -> None:
        """Open a role block, rejecting a nested or duplicate one."""
        if self.role is not None:
            raise PromptFormatError(
                path=self.path,
                line=line,
                reason="opened a new role block while another was still open",
                expected=f"</{self.role}> before opening <{role}>",
                got=f"<{role}>",
            )
        if role in self.seen:
            raise PromptFormatError(
                path=self.path,
                line=line,
                reason=f"duplicate <{role}> block",
                expected=f"at most one <{role}> block",
                got=f"second <{role}> block",
            )
        self.role = role
        self.role_start = line
        self.body = []

    def _close_block(self, role: Role, line: int) -> None:
        """Close the open role block, rejecting an unmatched or mismatched tag."""
        if self.role is None:
            raise PromptFormatError(
                path=self.path,
                line=line,
                reason=f"closing tag </{role}> without matching opening",
                expected="opening tag before closing",
                got=f"</{role}>",
            )
        if role != self.role:
            raise PromptFormatError(
                path=self.path,
                line=line,
                reason="mismatched closing tag",
                expected=f"</{self.role}>",
                got=f"</{role}>",
            )
        content = _verify_and_strip_h1(
            role=self.role,
            block_lines=self.body,
            block_start_line=self.role_start or line,
            path=self.path,
        )
        self.blocks.append((self.role, content))
        self.seen.add(self.role)
        self.role = None
        self.role_start = None
        self.body = []

    def _add_line(self, line: str) -> None:
        """Collect a content line when a block is open."""
        if self.role is not None:
            self.body.append(line)

    def _finish(self) -> tuple[tuple[Role, str], ...]:
        """Return the parsed blocks, rejecting an unclosed block or empty body."""
        if self.role is not None:
            raise PromptFormatError(
                path=self.path,
                line=self.role_start,
                reason=f"<{self.role}> block is not closed",
                expected=f"</{self.role}> before end of source",
                got="end of source",
            )
        if not self.blocks:
            raise PromptFormatError(
                path=self.path,
                line=None,
                reason="source contains no role blocks",
                expected="at least one <system>, <user>, or <assistant> block",
                got="zero role blocks",
            )
        return tuple(self.blocks)


def _verify_and_strip_h1(
    *,
    role: Role,
    block_lines: list[str],
    block_start_line: int,
    path: Path | None,
) -> str:
    """Verify the required H1 inside a block and strip it from the content."""
    expected_h1 = ROLE_H1[role]

    for offset, line in enumerate(block_lines):
        if line.strip() == "":
            continue
        if line.lstrip(" \t") != expected_h1:
            raise PromptFormatError(
                path=path,
                line=block_start_line + 1 + offset,
                reason=f"first non-blank line in <{role}> block must be the required H1",
                expected=expected_h1,
                got=line,
            )
        return _normalize_block_content(block_lines[offset + 1 :])

    raise PromptFormatError(
        path=path,
        line=block_start_line,
        reason=f"<{role}> block is empty; missing required H1",
        expected=expected_h1,
        got="(no content)",
    )


def _normalize_block_content(lines: list[str]) -> str:
    """Strip leading and trailing blank lines; preserve interior content verbatim."""
    start = 0
    end = len(lines)
    while start < end and lines[start].strip() == "":
        start += 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    return "\n".join(lines[start:end])
