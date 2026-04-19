"""litellm backend package.

All litellm imports are isolated to this package.
If litellm is removed, only this package changes.
"""

from openfactcheck.chat.backends.litellm.backend import LiteLLMBackend

__all__ = ["LiteLLMBackend"]
