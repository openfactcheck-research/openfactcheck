---
name: reviser
description: Rewrite a document to fix its factual errors, preserving style.
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

You are a helpful factchecker assistant.

</system>

<user>

# User Prompt

Given a document containing factual errors, correct the errors in the document depending on a corresponding list of factually true claims. Preserve the linguistic features and style of the original document; only correct the factual errors.

## Document

{{response}}

## True claims

{{claims}}

</user>
