"""Exception hierarchy for the prompts layer.

Every prompts-layer exception derives from [`PromptError`][PromptError].
Subclasses also inherit from the closest stdlib exception so code that
catches by stdlib type (``FileNotFoundError``, ``ValueError``,
``KeyError``) still works.

There are two ``ValueError`` subclasses:

- [`PromptFormatError`][PromptFormatError]: a codec-specific parse
  failure. Malformed YAML, broken tag structure, missing required H1,
  codec-local policy violation (for example, the markdown codec rejecting
  repeated roles). Only codecs raise this.
- [`PromptValidationError`][PromptValidationError]: a domain-invariant
  failure. Undeclared placeholder reference, invalid identifier. Raised
  from both codec-decoded and code-built templates because the rule is a
  property of the domain, not of any single format.

Users who want "something wrong with this prompt" catch
[`PromptError`][PromptError]. Users who want to branch on "bad file
format" vs "bad constructor input" catch the specific subclass.

Example:
    ```python
    from openfactcheck.prompts import (
        PromptError,
        PromptFormatError,
        PromptNotFoundError,
        PromptTemplate,
        PromptValidationError,
    )

    try:
        template = PromptTemplate.from_file("prompts/verifier.md")
    except PromptNotFoundError:
        ...  # no file at that path
    except PromptFormatError:
        ...  # bad YAML or tag structure in a markdown file
    except PromptValidationError:
        ...  # placeholder references an undeclared variable
    except PromptError:
        ...  # anything else from the prompts layer
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


INLINE_LOCATION = "(python)"
"""Placeholder used in [`PromptFormatError`][PromptFormatError] and
[`PromptValidationError`][PromptValidationError] messages when no
filesystem path is available (Python-constructed prompts)."""


class PromptError(Exception):
    """Base exception for every prompts-layer failure.

    Catch this to handle any failure from the prompts layer without
    branching on the specific cause.
    """


class PromptNotFoundError(PromptError, FileNotFoundError):
    """No prompt file was found at the requested path.

    Raised by [`PromptTemplate.from_file`][PromptTemplate.from_file] when the
    path does not exist. ``attempted_paths`` records the path(s) probed.
    """

    def __init__(self, prompt_name: str, attempted_paths: tuple[Path, ...]) -> None:
        """Record the prompt name and the paths that were probed."""
        self.prompt_name = prompt_name
        self.attempted_paths = attempted_paths
        joined = ", ".join(str(p) for p in attempted_paths) or "(none)"
        super().__init__(f"prompt {prompt_name!r} not found; attempted: {joined}")


class PromptFormatError(PromptError, ValueError):
    """A codec could not parse the source text into a [`PromptTemplate`][PromptTemplate].

    Covers YAML frontmatter errors, malformed tag structure, H1
    convention failures, and codec-local policy violations (for example,
    the markdown codec forbidding repeated role blocks). Format errors are
    always tied to a specific codec; the domain is not aware of any of them.

    Message shape::

        <path or '(python)'>:<line>: <reason>
          expected: <expected>
          got:      <got>
    """

    def __init__(
        self,
        *,
        path: Path | None,
        line: int | None,
        reason: str,
        expected: str | None = None,
        got: str | None = None,
    ) -> None:
        """Record the source location and reason for the parse failure."""
        self.path = path
        self.line = line
        self.reason = reason
        self.expected = expected
        self.got = got
        super().__init__(_format_message(path, line, reason, expected, got))


class PromptValidationError(PromptError, ValueError):
    """A [`PromptTemplate`][PromptTemplate] violates a domain invariant.

    Raised from both [`PromptCodec.decode`][openfactcheck.prompts.codecs.protocol.PromptCodec.decode] and
    [`PromptTemplate.from_messages`][PromptTemplate.from_messages] when the
    template would contain a placeholder that references no declared
    variable, an invalid identifier, or any other rule that holds regardless
    of how the template was authored.
    """

    def __init__(
        self,
        *,
        path: Path | None,
        line: int | None,
        reason: str,
        expected: str | None = None,
        got: str | None = None,
    ) -> None:
        """Record the location and reason for the invariant violation."""
        self.path = path
        self.line = line
        self.reason = reason
        self.expected = expected
        self.got = got
        super().__init__(_format_message(path, line, reason, expected, got))


class PromptVariableError(PromptError, KeyError):
    """Supplied values did not match the template's variable contract.

    Raised by [`PromptTemplate.to_prompt`][PromptTemplate.to_prompt] when a
    required variable is missing, or when an unexpected variable name is
    supplied.
    """

    def __init__(
        self,
        prompt_name: str,
        *,
        missing: tuple[str, ...] = (),
        unexpected: tuple[str, ...] = (),
    ) -> None:
        """Record which required variables were missing or unexpectedly supplied."""
        self.prompt_name = prompt_name
        self.missing = missing
        self.unexpected = unexpected
        details: list[str] = []
        if missing:
            details.append(f"missing={list(missing)}")
        if unexpected:
            details.append(f"unexpected={list(unexpected)}")
        super().__init__(
            f"prompt {prompt_name!r}: {', '.join(details) or 'no variable mismatch'}",
        )


def _format_message(
    path: Path | None,
    line: int | None,
    reason: str,
    expected: str | None,
    got: str | None,
) -> str:
    """Build the standard ``<path>:<line>: <reason>`` error message."""
    location = str(path) if path is not None else INLINE_LOCATION
    line_part = f":{line}" if line is not None else ""
    head = f"{location}{line_part}: {reason}"
    tail: list[str] = []
    if expected is not None:
        tail.append(f"  expected: {expected}")
    if got is not None:
        tail.append(f"  got:      {got}")
    return "\n".join([head, *tail])
