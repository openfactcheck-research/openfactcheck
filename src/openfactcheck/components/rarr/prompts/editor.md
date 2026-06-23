---
name: editor
description: Edit a passage to agree with evidence while changing as little as possible.
variables:
  claim:
    type: string
    required: true
  query:
    type: string
    required: true
  evidence:
    type: string
    required: true
---

<system>

# System Prompt

I will fix some things you said.

**You said:**

> Your nose switches back and forth between nostrils. When you sleep, you switch about every 45 minutes. This is to prevent a buildup of mucus. It's called the nasal cycle.

**I checked:** How often do your nostrils switch?

**I found this article:**

> Although we don't usually notice it, during the nasal cycle one nostril becomes congested and thus contributes less to airflow, while the other becomes decongested. On average, the congestion pattern switches about every 2 hours, according to a small 2016 study published in the journal PLOS One.

**Reasoning:** This suggests 45 minutes switch time in your statement is wrong.

**Fix:**

> Your nose switches back and forth between nostrils. When you sleep, you switch about every 2 hours. This is to prevent a buildup of mucus. It's called the nasal cycle.

**You said:**

> In the battles of Lexington and Concord, the British side was led by General Thomas Hall.

**I checked:** Who led the British side in the battle of Lexington and Concord?

**I found this article:**

> Interesting Facts about the Battles of Lexington and Concord. The British were led by Lieutenant Colonel Francis Smith. There were 700 British regulars.

**Reasoning:** This suggests General Thomas Hall in your statement is wrong.

**Fix:**

> In the battles of Lexington and Concord, the British side was led by Lieutenant Colonel Francis Smith.

**You said:**

> The Stanford Prison Experiment was conducted in the basement of Encina Hall, Stanford's psychology building.

**I checked:** Where was Stanford Prison Experiment conducted?

**I found this article:**

> Carried out August 15-21, 1971 in the basement of Jordan Hall, the Stanford Prison Experiment set out to examine the psychological effects of authority and powerlessness in a prison environment.

**Reasoning:** This suggests Encina Hall in your statement is wrong.

**Fix:**

> The Stanford Prison Experiment was conducted in the basement of Jordan Hall, Stanford's psychology building.

**You said:**

> The Havel-Hakimi algorithm is an algorithm for converting the adjacency matrix of a graph into its adjacency list. It is named after Vaclav Havel and Samih Hakimi.

**I checked:** What is the Havel-Hakimi algorithm?

**I found this article:**

> The Havel-Hakimi algorithm constructs a special solution if a simple graph for the given degree sequence exists, or proves that one cannot find a positive answer. This construction is based on a recursive algorithm. The algorithm was published by Havel (1955), and later by Hakimi (1962).

**Reasoning:** This suggests the Havel-Hakimi algorithm's functionality in your statement is wrong.

**Fix:**

> The Havel-Hakimi algorithm constructs a special solution if a simple graph for the given degree sequence exists, or proves that one cannot find a positive answer. It is named after Vaclav Havel and Samih Hakimi.

**You said:**

> "Time of My Life" is a song by American singer-songwriter Bill Medley from the soundtrack of the 1987 film Dirty Dancing. The song was produced by Phil Ramone.

**I checked:** Who was the producer of "(I've Had) The Time of My Life"?

**I found this article:**

> On September 8, 2010, the original demo of this song, along with a remix by producer Michael Lloyd , was released as digital files in an effort to raise money for the Patrick Swayze Pancreas Cancer Resarch Foundation at Stanford University.

**Reasoning:** This suggests "Time of My Life" producer name in your statement is wrong.

**Fix:**

> "Time of My Life" is a song by American singer-songwriter Bill Medley from the soundtrack of the 1987 film Dirty Dancing. The song was produced by Michael Lloyd.

**You said:**

> Phoenix Market City Pune is located on 21 acres of prime property in Pune. It is spread across four levels with approximately 1.4 million square feet of built-up space. The mall is owned and operated by Phoenix Mills Limited.

**I checked:** What is the area of Phoenix Market City in Pune?

**I found this article:**

> Phoenix Market City was opened in January 2013 and has the distinction of being the largest mall in the city of Pune, with the area of 3.4 million square feet. It is located in the Viman Nagar area of Pune.

**Reasoning:** This suggests the 1.4 million square feet of built-up space in your statment is wrong.

**Fix:**

> Phoenix Market City Pune is located on 21 acres of prime property in Pune. It is spread across four levels with approximately 3.4 million square feet of built-up space. The mall is owned and operated by Phoenix Mills Limited.

</system>

<user>

# User Prompt

**You said:**

> {{claim}}

**I checked:** {{query}}

**I found this article:**

> {{evidence}}

**Reasoning:**

</user>
