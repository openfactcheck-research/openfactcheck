---
name: reviser
description: Revise a document to fix its factual errors, preserving style.
variables:
  response:
    type: string
    required: true
  claims:
    type: string
    required: true
---

<system>

# System Prompt

Given a document containing factual errors, please correct the errors in the document depending on a corresponding list of factually true claims. Note that preserve the linguistic features and style of the original document, just correct factual errors.

</system>

<user>

# User Prompt

document: {{response}}

true claims: {{claims}}

revised document:

</user>
