"""OpenAI SDK backend package.

All ``openai`` SDK imports are isolated to this package.
If the SDK is removed, only this package changes.
"""

from openfactcheck.chat.backends.openai.backend import OpenAIBackend

__all__ = ["OpenAIBackend"]
