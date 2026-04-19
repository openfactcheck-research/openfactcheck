# OpenFactCheck

Python framework for fact-checking with LLM pipelines.

## Install

```bash
pip install openfactcheck[openai,anthropic]
```

## Quickstart

```python
from openfactcheck.chat import ChatClient, OpenAIConfig, UserMessage

client = ChatClient(config=OpenAIConfig(model="gpt-4o"))
response = client.completion([UserMessage(content="Hello!")])
print(response.message.content)
```

## Reference

- [Chat config](reference/chat/config.md) — provider-specific configuration for model calls.
- [API auth](reference/api/auth/index.md) — token verifiers for the REST API.
