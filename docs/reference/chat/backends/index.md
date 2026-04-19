# Backends

::: openfactcheck.chat.backends
    options:
      members: false
      show_root_heading: false

## Pages

- [`ChatBackend` protocol](base.md) — the interface every backend satisfies.
- [`OpenAIBackend` class](openai.md) — direct-SDK backend for OpenAI.
- [`AnthropicBackend` class](anthropic.md) — direct-SDK backend for Anthropic.
- [`LangChainBackend` class](langchain.md) — route through LangChain.
- [`LiteLLMBackend` class](litellm.md) — route through litellm.
