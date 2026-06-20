---
name: query_generator
description: Generate comprehensive questions to verify the information in a passage.
variables:
  input:
    type: string
    required: true
---

<system>

# System Prompt

You will check things people say and ask questions.

</system>

<user>

# User Prompt

I will check things you said and ask questions. For the given passage, generate the questions you would search to verify the information in it.

## Examples

**You said:** Your nose switches back and forth between nostrils. When you sleep, you switch about every 45 minutes. This is to prevent a buildup of mucus. It's called the nasal cycle.

**To verify it, I would search:**

- Does your nose switch between nostrils?
- How often does your nostrils switch?
- Why does your nostril switch?
- What is nasal cycle?

**You said:** The Stanford Prison Experiment was conducted in the basement of Encina Hall, Stanford's psychology building.

**To verify it, I would search:**

- Where was Stanford Prison Experiment was conducted?

**You said:** The Havel-Hakimi algorithm is an algorithm for converting the adjacency matrix of a graph into its adjacency list. It is named after Vaclav Havel and Samih Hakimi.

**To verify it, I would search:**

- What does Havel-Hakimi algorithm do?
- Who are Havel-Hakimi algorithm named after?

**You said:** "Time of My Life" is a song by American singer-songwriter Bill Medley from the soundtrack of the 1987 film Dirty Dancing. The song was produced by Michael Lloyd.

**To verify it, I would search:**

- Who sings the song "Time of My Life"?
- Which film is the song "Time of My Life" from?
- Who produced the song "Time of My Life"?

**You said:** Kelvin Hopins was suspended from the Labor Party due to his membership in the Conservative Party.

**To verify it, I would search:**

- Why was Kelvin Hopins suspended from Labor Party?

**You said:** Social work is a profession that is based in the philosophical tradition of humanism. It is an intellectual discipline that has its roots in the 1800s.

**To verify it, I would search:**

- What philosophical tradition is social work based on?
- What year does social work have its root in?

## Passage to verify

{{input}}

</user>
