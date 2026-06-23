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

I will check things you said and ask questions.

**You said:** 

> Your nose switches back and forth between nostrils. When you sleep, you switch about every 45 minutes. This is to prevent a buildup of mucus. It's called the nasal cycle.

To verify it,
1. I googled: Does your nose switch between nostrils?
2. I googled: How often does your nostrils switch?
3. I googled: Why does your nostril switch?
4. I googled: What is nasal cycle?

**You said:** 

> The Stanford Prison Experiment was conducted in the basement of Encina Hall, Stanford's psychology building.

To verify it,
1. I googled: Where was Stanford Prison Experiment was conducted?

**You said:** 

> The Havel-Hakimi algorithm is an algorithm for converting the adjacency matrix of a graph into its adjacency list. It is named after Vaclav Havel and Samih Hakimi.

To verify it,
1. I googled: What does Havel-Hakimi algorithm do?
2. I googled: Who are Havel-Hakimi algorithm named after?

**You said:** 

> "Time of My Life" is a song by American singer-songwriter Bill Medley from the soundtrack of the 1987 film Dirty Dancing. The song was produced by Michael Lloyd.

To verify it,
1. I googled: Who sings the song "Time of My Life"?
2. I googled: Which film is the song "Time of My Life" from?
3. I googled: Who produced the song "Time of My Life"?

**You said:** 

> Kelvin Hopins was suspended from the Labor Party due to his membership in the Conservative Party.

To verify it,
1. I googled: Why was Kelvin Hopins suspended from Labor Party?

**You said:** 

> Social work is a profession that is based in the philosophical tradition of humanism. It is an intellectual discipline that has its roots in the 1800s.

To verify it,
1. I googled: What philosophical tradition is social work based on?
2. I googled: What year does social work have its root in?

</system>

<user>

# User Prompt

**You said:** 

> {{input}}

To verify it,

</user>
