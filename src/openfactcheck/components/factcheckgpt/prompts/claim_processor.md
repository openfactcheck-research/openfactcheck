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

## Claim Decomposition

Your first task is to decompose the text into atomic claims. 

Let's define a function named `decompose(input:str)`. The returned value should be a list of strings, where each string should be a context-independent claim, representing one fact.

### Example

**Text:** 

> Mary is a five-year old girl, she likes playing piano and she doesn't like cookies.

**Atomic Claims:**
- Mary is a five-year old girl.
- Mary likes playing piano.
- Mary doesn't like cookies.

## Claim Checkworthiness

Your second task is to identify whether each atomic claim is checkworthy in the context of fact-checking. 

Let's define a function named `checkworthy(input: List[str])`. The return value should be a list of strings, where each string selects from ["Yes", "No"].

- "Yes" means the text is a factual checkworthy statement.
- "No" means that the text is not checkworthy, it might be an opinion, a question, or others.

### Examples

**Text:** 

> I think Apple is a good company.  

**Checkworthiness:** "No"

**Text:** 

> Friends is a great TV series.

**Checkworthiness:** "Yes"

**Text:** 

> Are you sure Preslav is a professor in MBZUAI?  

**Checkworthiness:** "No"

**Text:** 

> The Stanford Prison Experiment was conducted in the basement of Encina Hall.  

**Checkworthiness:** "Yes"

**Text:** 

> As a language model, I can't provide these info.

**Checkworthiness:** "No"

</system>

<user>

# User Prompt

checkworthy(decompose({{input}}))

</user>
