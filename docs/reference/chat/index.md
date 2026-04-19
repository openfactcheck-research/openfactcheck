# Chat

::: openfactcheck.chat
    options:
      members: false
      show_root_heading: false

## Pages

- [`ChatClient` class](client.md) — the facade callers use to send messages and receive completions or streams.
- [Messages](messages.md) — system, user, assistant, and tool messages that flow through the client.
- [Requests](requests.md) — the bundled payload a backend receives (messages + config + runtime).
- [Responses](responses.md) — complete responses, streaming events, and usage data.
- [Config](config.md) — provider-specific configuration and runtime settings.
- [Errors](errors.md) — exception hierarchy raised by the chat client and backends.
- [Providers](providers/index.md) — provider-level capability declaration and configuration validation.
- [Backends](backends/index.md) — the replaceable execution boundary that talks to the underlying SDK.
