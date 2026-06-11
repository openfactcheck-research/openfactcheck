"""Public API for the prompts layer.

Build a [`PromptTemplate`][PromptTemplate] from chat messages with
``{{variables}}`` (or load one from a file with
[`PromptTemplate.from_file`][PromptTemplate.from_file]), then fill it: to a
chat message list with [`to_messages`][PromptTemplate.to_messages], to a
[`Prompt`][Prompt] value with [`to_prompt`][PromptTemplate.to_prompt], or to a
single string with [`to_string`][PromptTemplate.to_string].

Import everything from ``openfactcheck.prompts`` directly; submodule paths are
not part of the public API.

Example:
    ```python
    from openfactcheck.prompts import PromptTemplate

    verifier = PromptTemplate.from_messages(
        [
            ("system", "You are a fact-checker."),
            ("user", "Claim: {{claim}}"),
        ],
        name="verifier",
    )
    messages = verifier.to_messages(claim="The sky is green.")
    ```
"""

from openfactcheck.prompts.codecs import MarkdownPromptCodec, PromptCodec
from openfactcheck.prompts.errors import (
    PromptError,
    PromptFormatError,
    PromptNotFoundError,
    PromptValidationError,
    PromptVariableError,
)
from openfactcheck.prompts.prompt import Prompt
from openfactcheck.prompts.template import PromptTemplate
from openfactcheck.prompts.variables import Role, VariableSpec

# Templates and filled prompts
__all__ = [
    "Prompt",
    "PromptTemplate",
]

# Variables
__all__ += [
    "Role",
    "VariableSpec",
]

# Codecs
__all__ += [
    "MarkdownPromptCodec",
    "PromptCodec",
]

# Errors
__all__ += [
    "PromptError",
    "PromptFormatError",
    "PromptNotFoundError",
    "PromptValidationError",
    "PromptVariableError",
]
