# Errors

::: openfactcheck.chat.errors
    options:
      members: false
      show_root_heading: false

## Base

::: openfactcheck.chat.errors.ChatModelError
    options:
      show_root_heading: true
      heading_level: 3

## Specific failures

::: openfactcheck.chat.errors.ProviderNotFoundError
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.chat.errors.AuthenticationError
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.chat.errors.RateLimitError
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.chat.errors.ProviderError
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.chat.errors.UnsupportedFeatureError
    options:
      show_root_heading: true
      heading_level: 3
