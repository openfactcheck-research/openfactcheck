"""Markdown codec: YAML frontmatter + role-tagged body blocks.

Accepts and emits prompts in a YAML-frontmatter, role-tagged markdown format.
The rules below are codec-local, not domain invariants.

Authoring rules:

1. File starts with a YAML frontmatter block delimited by ``---`` lines.
2. Body contains zero or more role blocks delimited by ``<system>``,
   ``<user>``, ``<assistant>`` (and their closers) on their own lines at
   column 0. Content outside role blocks is documentation and ignored.
3. At most one block of each role; at least one role block total. The domain
   permits repeated roles; this codec does not.
4. Inside each block, the first non-blank line must exactly match the
   canonical H1 (``# System Prompt`` / ``# User Prompt`` /
   ``# Assistant Prompt``). The H1 is stripped from the message content; it
   labels the block for human readers, and the model never sees it.
"""

from openfactcheck.prompts.codecs.markdown.codec import MarkdownPromptCodec

__all__ = ["MarkdownPromptCodec"]
