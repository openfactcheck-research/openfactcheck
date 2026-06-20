---
name: agreement_gate
description: Decide whether a passage agrees with evidence on the answer to a question.
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

You will check some things people say against evidence.

</system>

<user>

# User Prompt

I will check some things you said. For the answer to the question, compare what you said against the article I found. State your **reasoning** about the answer each implies, then give your **decision**: `agrees` if they agree, `disagrees` if they disagree, or `irrelevant` if the article does not answer the question.

## Examples

- **You said:** Your nose switches back and forth between nostrils. When you sleep, you switch about every 45 minutes. This is to prevent a buildup of mucus. It's called the nasal cycle.
- **I checked:** How often do your nostrils switch?
- **I found this article:** Although we don't usually notice it, during the nasal cycle one nostril becomes congested and thus contributes less to airflow, while the other becomes decongested. On average, the congestion pattern switches about every 2 hours, according to a small 2016 study published in the journal PLOS One.
- **Reasoning:** The article said the nose's switching time is about every 2 hours, and you said the nose's switching time is about every 45 minutes.
- **Decision:** disagrees

- **You said:** The Little House books were written by Laura Ingalls Wilder. The books were published by HarperCollins.
- **I checked:** Who published the Little House books?
- **I found this article:** These are the books that started it all -- the stories that captured the hearts and imaginations of children and young adults worldwide. Written by Laura Ingalls Wilder and published by HarperCollins, these beloved books remain a favorite to this day.
- **Reasoning:** The article said the Little House books were published by HarperCollins and you said the books were published by HarperCollins.
- **Decision:** agrees

- **You said:** Real Chance of Love was an American reality TV show. Season 2 of the show was won by Cali, who chose to be with Chance.
- **I checked:** Who won season 2 of Real Chance of Love?
- **I found this article:** Real Chance of Love 2: Back in the Saddle is the second season of the VH1 reality television dating series Real Chance of Love. Ahmad Givens (Real) and Kamal Givens (Chance), former contestants on I Love New York are the central figures.
- **Reasoning:** The article doesn't answer the question and you said that Cali won season 2 of Real Chance of Love.
- **Decision:** irrelevant

- **You said:** The Stanford Prison Experiment was conducted in the basement of Jordan Hall, Stanford's psychology building.
- **I checked:** Where was Stanford Prison Experiment conducted?
- **I found this article:** Carried out August 15-21, 1971 in the basement of Jordan Hall, the Stanford Prison Experiment set out to examine the psychological effects of authority and powerlessness in a prison environment.
- **Reasoning:** The article said the Stanford Prison Experiment was conducted in Jordan Hall and you said the Stanford Prison Experiment was conducted in Jordan Hall.
- **Decision:** agrees

- **You said:** Social work is a profession that is based in the philosophical tradition of humanism. It is an intellectual discipline that has its roots in the 1800s.
- **I checked:** When did social work have its roots?
- **I found this article:** The Emergence and Growth of the Social work Profession. Social work's roots were planted in the 1880s, when charity organization societies (COS) were created to organize municipal voluntary relief associations and settlement houses were established.
- **Reasoning:** The article said social work has its roots planted in the 1880s and you said social work has its root in the 1800s.
- **Decision:** disagrees

- **You said:** The Havel-Hakimi algorithm is an algorithm for converting the adjacency matrix of a graph into its adjacency list. It is named after Vaclav Havel and Samih Hakimi.
- **I checked:** What is the Havel-Hakimi algorithm?
- **I found this article:** The Havel-Hakimi algorithm constructs a special solution if a simple graph for the given degree sequence exists, or proves that one cannot find a positive answer. This construction is based on a recursive algorithm. The algorithm was published by Havel (1955), and later by Hakimi (1962).
- **Reasoning:** The article said the Havel-Hakimi algorithm is for constructing a special solution if a simple graph for the given degree sequence exists and you said the Havel-Hakimi algorithm is for converting the adjacency matrix of a graph.
- **Decision:** disagrees

- **You said:** "Time of My Life" is a song by American singer-songwriter Bill Medley from the soundtrack of the 1987 film Dirty Dancing. The song was produced by Michael Lloyd.
- **I checked:** Who was the producer of "(I've Had) The Time of My Life"?
- **I found this article:** On September 8, 2010, the original demo of this song, along with a remix by producer Michael Lloyd, was released as digital files in an effort to raise money for the Patrick Swayze Pancreas Cancer Resarch Foundation at Stanford University.
- **Reasoning:** The article said that a demo was produced by Michael Lloyd and you said "Time of My Life" was produced by Michael Lloyd.
- **Decision:** agrees

- **You said:** Tiger Woods is the only player who has won the most green jackets. He has won four times. The Green Jacket is one of the most coveted prizes in all of golf.
- **I checked:** What is the Green Jacket in golf?
- **I found this article:** The green jacket is a classic, three-button, single-breasted and single-vent, featuring the Augusta National Golf Club logo on the left chest pocket. The logo also appears on the brass buttons.
- **Reasoning:** The article said the Green Jacket is a classic three-button single-breasted and single-vent and you said the Green Jacket is one of the most coveted prizes in all of golf.
- **Decision:** irrelevant

- **You said:** Kelvin Hopins was suspended from the Labor Party because he had allegedly sexually harassed and behaved inappropriately towards a Labour Party activist, Ava Etemadzadeh.
- **I checked:** Why was Kelvin Hopins suspeneded from the Labor Party?
- **I found this article:** A former Labour MP has left the party before an inquiry into sexual harassment allegations against him was able to be concluded, the party has confirmed. Kelvin Hopkins was accused in 2017 of inappropriate physical contact and was suspended by the Labour party pending an investigation.
- **Reasoning:** The article said Kelvin Hopins was suspended because of inappropriate physical contact and you said that Kelvin Hopins was suspended because he allegedly sexually harassed Ava Etemadzadeh.
- **Decision:** agrees

- **You said:** In the battles of Lexington and Concord, the British side was led by General Thomas Smith.
- **I checked:** Who led the British side in the battle of Lexington and Concord?
- **I found this article:** Interesting Facts about the Battles of Lexington and Concord. The British were led by Lieutenant Colonel Francis Smith. There were 700 British regulars.
- **Reasoning:** The article said the British side was led by Lieutenant Colonel Francis Smith and you said the British side was led by General Thomas Smith.
- **Decision:** disagrees

## Now check

- **You said:** {{claim}}
- **I checked:** {{query}}
- **I found this article:** {{evidence}}

</user>
