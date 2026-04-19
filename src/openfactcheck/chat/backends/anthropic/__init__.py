"""Anthropic SDK backend package.

All ``anthropic`` SDK imports are isolated to this package.
If the SDK is removed, only this package changes.
"""

from openfactcheck.chat.backends.anthropic.backend import AnthropicBackend

__all__ = ["AnthropicBackend"]
