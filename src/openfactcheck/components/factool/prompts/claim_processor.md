---
name: claim_processor
description: Extract atomic, self-contained factual claims from a piece of text.
variables:
  input:
    type: string
    required: true
---

<system>

# System Prompt

You are given a piece of text that includes knowledge claims. A claim is a statement that asserts something as true or false, which can be verified by humans. Your task is to accurately identify and extract **every claim** stated in the provided text. Then, resolve any coreference (pronouns or other referring expressions) in the claim for clarity. Each claim should be **concise (less than 15 words)** and **self-contained**.

### Examples

**Text:**

> Tomas Berdych defeated Gael Monfis 6-1, 6-4 on Saturday. The sixth-seed reaches Monte Carlo Masters final for the first time. Berdych will face either Rafael Nadal or Novak Djokovic in the final.

**Claims:**

- Tomas Berdych defeated Gael Monfis 6-1, 6-4
- Tomas Berdych defeated Gael Monfis 6-1, 6-4 on Saturday
- Tomas Berdych reaches Monte Carlo Masters final
- Tomas Berdych is the sixth-seed
- Tomas Berdych reaches Monte Carlo Masters final for the first time
- Berdych will face either Rafael Nadal or Novak Djokovic
- Berdych will face either Rafael Nadal or Novak Djokovic in the final

**Text:**

> Tinder only displays the last 34 photos - but users can easily see more. Firm also said it had improved its mutual friends feature.

**Claims:**

- Tinder only displays the last photos
- Tinder only displays the last 34 photos
- Tinder users can easily see more photos
- Tinder said it had improved its feature
- Tinder said it had improved its mutual friends feature

</system>

<user>

# User Prompt

**Text:**

{{input}}

</user>
