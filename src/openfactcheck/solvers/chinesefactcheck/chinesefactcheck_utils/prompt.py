"""All prompts used for fact-checking subtasks prompting."""

CLAIM_EXTRACTION_PROMPT = {
    "system": "请提供您想要查证的陈述。",
    "user": """你将看到一段包含知识性陈述的文本。一个陈述是指声称某件事为真或假的句子，并且可以被人类验证。你的任务是准确识别并提取文本中的每一个陈述。然后，将陈述中的指代（如代词等）解析为具体对象，使其更清晰。每条陈述应简洁（少于15个词）并且独立完整。

你的回答**必须**是一个字典列表。每个字典应包含一个键 "claim"，其对应值是提取出的陈述（已经解析了所有指代关系）。

你**只能**按照如下格式作答。**不得添加任何额外说明或违反格式的内容**。你的回答**必须以 '[' 开始**。

[回答格式]: 
[
    {{
    "claim": "确保陈述少于15个词，表达完整清晰的意思。解析所有指代。",
    }},
    ...
]

以下是两个例子：
[text]: Tomas Berdych 于星期六以 6-1、6-4 击败 Gael Monfis。这位六号种子首次晋级蒙特卡洛大师赛决赛。Berdych 将在决赛中迎战 Rafael Nadal 或 Novak Djokovic。
[response]: [{{"claim": "Tomas Berdych 以 6-1、6-4 击败 Gael Monfis"}}, {{"claim": "Tomas Berdych 于星期六以 6-1、6-4 击败 Gael Monfis"}}, {{"claim": "Tomas Berdych 晋级蒙特卡洛大师赛决赛"}}, {{"claim": "Tomas Berdych 是六号种子"}}, {{"claim": "Tomas Berdych 首次晋级蒙特卡洛大师赛决赛"}}, {{"claim": "Tomas Berdych 将迎战 Rafael Nadal 或 Novak Djokovic"}}, {{"claim": "Tomas Berdych 将在决赛中迎战 Rafael Nadal 或 Novak Djokovic"}}]

[text]: Tinder 只显示最近的 34 张照片，但用户可以轻松查看更多。该公司还表示其改善了“共同好友”功能。
[response]: [{{"claim": "Tinder 只显示最近的照片"}}, {{"claim": "Tinder 只显示最近的 34 张照片"}}, {{"claim": "Tinder 用户可以轻松查看更多照片"}}, {{"claim": "Tinder 表示其改善了一个功能"}}, {{"claim": "Tinder 表示其改善了共同好友功能"}}]

现在完成以下任务，仅用列表格式作答，不要添加其他内容！！！
[text]: {input}
[response]: 
"""
}

QUERY_GENERATION_PROMPT = {
    "system": "你是一个查询生成器，用于生成简洁高效的搜索引擎查询，以验证给定的陈述。你只能用 Python 列表格式作答（不得包含其他任何内容）",
    "user": """你是一个查询生成器，旨在帮助用户使用搜索引擎验证给定的陈述。你的主要任务是为用户生成一个包含两个有效且具有怀疑性的搜索引擎查询的 Python 列表。这些查询应有助于用户批判性地评估该陈述的真实性。

你只能按照以下格式作答（Python 列表，每项为一个查询语句）。**请严格遵守格式，不要返回任何其他内容。你的回答必须以 '[' 开始，以 ']' 结束。**

[回答格式]: ['query1', 'query2']

以下是三个示例：
claim: 推特的 CEO 是比尔·盖茨。
response: ["谁是推特的 CEO？", "推特 CEO"]

claim: 迈克尔·菲尔普斯是历史上获得奖牌最多的奥运选手。
response: ["谁是历史上获得奖牌最多的奥运选手？", "迈克尔·菲尔普斯"]

claim: ChatGPT 是谷歌开发的。
response: ["ChatGPT 是谁开发的？", "ChatGPT 开发者"]

现在完成以下任务（**只用列表格式作答，不要返回其他内容！必须以 '[' 开始并以 ']' 结束**）：
claim: {input}
response: 
"""
}

VERIFICATION_PROMPT = {
    "system": "你是一个聪明的助手。",
    "user": """你将收到一段文本。你的任务是判断这段文本中是否存在任何事实性错误。

在判断文本的真实性时，你可以参考所提供的证据（如果需要）。这些证据可能有帮助，但有些证据可能相互矛盾。在使用证据判断文本真实性时必须谨慎。

你的回答应为一个包含四个键的字典："reasoning"、"factuality"、"error" 和 "correction"。它们分别对应推理过程、文本是否真实（布尔值 True 或 False）、文本中的事实错误（如有），以及修正后的文本。

以下是给定的文本
[text]: {claim}
以下是提供的证据
[evidences]: {evidence}

你必须严格按照以下格式作答。**不要返回任何其他内容**，**回答必须以 '{{' 开始**。
[回答格式]: 
{{
    "reasoning": "为什么这段文本是真实或不真实的？当你认为文本不真实时必须谨慎，并且必须提供多个证据来支持你的结论。",
    "error": "如果文本真实，则为 None；否则，请描述该错误。",
    "correction": "如果有错误，请给出修正后的文本。",
    "factuality": 如果文本真实则为 True，否则为 False。
}}
"""
}

CHINESE_TO_ENGLISH_TRANSLATION_PROMPT = {
    "system": "You are a helpful assistant.",
    "user": """You are given a piece of text in Chinese. Your task is to translate it into English. The translation should be accurate and maintain the original meaning of the text. Please ensure that the translation is grammatically correct and coherent in English.
DO NOT RESPOND WITH ANYTHING ELSE. ADDING ANY OTHER EXTRA NOTES THAT VIOLATE THE RESPONSE FORMAT IS BANNED. 

{input}
""",
}

ENGLISH_TO_CHINESE_TRANSLATION_PROMPT = {
    "system": "You are a helpful assistant.",
    "user": """You are given a piece of text in English. Your task is to translate it into Chinese. The translation should be accurate and maintain the original meaning of the text. Please ensure that the translation is grammatically correct and coherent in Chinese.
DO NOT RESPOND WITH ANYTHING ELSE. ADDING ANY OTHER EXTRA NOTES THAT VIOLATE THE RESPONSE FORMAT IS BANNED.

{input}
""",
}
