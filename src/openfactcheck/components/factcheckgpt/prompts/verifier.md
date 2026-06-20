---
name: verifier
description: Judge whether a claim is factual against evidence, and correct it if not.
variables:
  claim:
    type: string
    required: true
  evidence:
    type: string
    required: true
---

<system>

# System Prompt

You are a helpful factchecker assistant.

</system>

<user>

# User Prompt

You are given a piece of text. Your task is to identify whether there are any **factual errors** within the text.

When you judge the factuality of the given text, you may reference the provided evidence if needed. The provided evidence may be helpful. Some evidence may contradict each other, so you must be careful when using it to judge the factuality of the given text.

Provide your **reasoning** for whether the text is factual or not. Be careful: when you decide something is non-factual, you must point to evidence supporting your decision. Then decide the **factuality** of the text: **true** if it is factual, **false** otherwise. If there is a factual error, describe the **error** and provide a **correction** of the text; if the text is factual, leave the error and correction empty.

## Text

{{claim}}

## Evidence

{{evidence}}

</user>
