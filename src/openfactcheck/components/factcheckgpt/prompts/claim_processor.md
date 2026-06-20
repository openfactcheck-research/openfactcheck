---
name: claim_processor
description: Decompose text into atomic, context-independent, checkworthy factual claims.
variables:
  input:
    type: string
    required: true
---

<system>

# System Prompt

You are good at decomposing and decontextualizing text.

</system>

<user>

# User Prompt

Your task is to decompose the text into atomic claims, keeping only the ones worth fact-checking.

- Each claim should be a context-independent claim, representing one fact. Resolve coreferences (pronouns and other referring expressions) to the entities they refer to, so each claim stands on its own.
- Keep only **checkworthy** claims: factual statements that can be verified. Drop opinions, questions, imperatives, and anything else that is not a verifiable fact.

## Examples

**Text:**

> Mary is a five-year old girl, she likes playing piano and she doesn't like cookies.

**Claims:**

- Mary is a five-year old girl.
- Mary likes playing piano.
- Mary doesn't like cookies.

**Text:**

> I think Apple is a great company. Apple was founded in 1976 by Steve Jobs and Steve Wozniak.

**Claims:**

- Apple was founded in 1976.
- Apple was founded by Steve Jobs and Steve Wozniak.

## Text to decompose

{{input}}

</user>
