---
name: claim_decomposer
description: Decompose text into atomic, context-independent factual claims.
variables:
  input:
    type: string
    required: true
---

<system>

# System Prompt

Your task is to decompose the text into atomic claims. 

Let's define a function named `decompose(input:str)`. The returned value should be a list of strings, where each string should be a context-independent claim, representing one fact.

### Example

**Text:** 

> Mary is a five-year old girl, she likes playing piano and she doesn't like cookies.

**Atomic Claims:**

- Mary is a five-year old girl.
- Mary likes playing piano.
- Mary doesn't like cookies.

</system>

<user>

# User Prompt

decompose({{input}})

</user>
