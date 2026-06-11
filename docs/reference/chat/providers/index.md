# Providers

::: openfactcheck.chat.providers
    options:
      members: false
      show_root_heading: false

## Lookup

::: openfactcheck.chat.providers.get_provider
    options:
      show_root_heading: true
      heading_level: 3

## Pages

- [`BaseProvider` class](base.md): the abstract base every provider extends.
- [`OpenAIProvider` class](openai.md): concrete provider for OpenAI models.
- [`OpenRouterProvider` class](openrouter.md): concrete provider for OpenRouter models.
- [`AnthropicProvider` class](anthropic.md): concrete provider for Anthropic models.
