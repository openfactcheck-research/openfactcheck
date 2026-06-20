---
name: query_generator
description: Generate web search queries that help verify a claim.
variables:
  input:
    type: string
    required: true
---

<system>

# System Prompt

You are a helpful factchecker assistant.

</system>

<user>

# User Prompt

I will check things you said and ask questions. For the given claim, generate the search engine queries you would look up to verify it.

## Examples

**Claim:** Your nose switches back and forth between nostrils. When you sleep, you switch about every 45 minutes. This is to prevent a buildup of mucus. It's called the nasal cycle.

**Queries:**

- Does your nose switch between nostrils?
- How often does your nostrils switch?
- Why does your nostril switch?
- What is nasal cycle?

**Claim:** The Stanford Prison Experiment was conducted in the basement of Encina Hall, Stanford's psychology building.

**Queries:**

- Where was Stanford Prison Experiment conducted?

**Claim:** The Havel-Hakimi algorithm is an algorithm for converting the adjacency matrix of a graph into its adjacency list. It is named after Vaclav Havel and Samih Hakimi.

**Queries:**

- What does Havel-Hakimi algorithm do?
- Who are Havel-Hakimi algorithm named after?

**Claim:** "Time of My Life" is a song by American singer-songwriter Bill Medley from the soundtrack of the 1987 film Dirty Dancing. The song was produced by Michael Lloyd.

**Queries:**

- Who sings the song "Time of My Life"?
- Which film is the song "Time of My Life" from?
- Who produced the song "Time of My Life"?

**Claim:** Kelvin Hopins was suspended from the Labor Party due to his membership in the Conservative Party.

**Queries:**

- Why was Kelvin Hopins suspended from Labor Party?

**Claim:** Social work is a profession that is based in the philosophical tradition of humanism. It is an intellectual discipline that has its roots in the 1800s.

**Queries:**

- What philosophical tradition is social work based on?
- What year does social work have its root in?

## Claim to verify

{{input}}

</user>
