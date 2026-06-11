# Chat configuration

::: openfactcheck.chat.config
    options:
      members: false
      show_root_heading: false

## Base

::: openfactcheck.chat.config.BaseModelConfig
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.chat.config.OpenAICompatibleConfig
    options:
      show_root_heading: true
      heading_level: 3

## Provider configs

::: openfactcheck.chat.config.OpenAIConfig
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.chat.config.OpenRouterConfig
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.chat.config.AnthropicConfig
    options:
      show_root_heading: true
      heading_level: 3

## Union type

::: openfactcheck.chat.config.ModelConfig
    options:
      show_root_heading: true
      heading_level: 3

## Runtime

::: openfactcheck.chat.config.RuntimeConfig
    options:
      show_root_heading: true
      heading_level: 3

## Provider name

::: openfactcheck.chat.config.ProviderName
    options:
      show_root_heading: true
      heading_level: 3
