"""LangChain backend package.

All LangChain/provider SDK imports are isolated to this package.
If LangChain is removed, only this package changes.
"""

from openfactcheck.chat.backends.langchain.backend import LangChainBackend

__all__ = ["LangChainBackend"]
