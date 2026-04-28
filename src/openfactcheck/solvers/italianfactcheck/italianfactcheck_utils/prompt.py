"""All prompts used for fact-checking subtasks prompting."""

"""All prompts used for fact-checking subtasks prompting."""

CLAIM_EXTRACTION_PROMPT = {
    "system": "Per favore fornisci l'affermazione che desideri verificare.",
    "user": """Ti viene fornito un testo che include affermazioni di conoscenza. Un'affermazione è una frase che afferma qualcosa come vero o falso e che può essere verificata dagli esseri umani. Il tuo compito è identificare ed estrarre accuratamente ogni affermazione presente nel testo fornito. Poi, risolvi qualsiasi coreferenza (pronomi o altre espressioni di riferimento) nell'affermazione per maggiore chiarezza. Ogni affermazione deve essere concisa (meno di 15 parole) e autosufficiente.
La tua risposta DEVE essere una lista di dizionari. Ogni dizionario deve contenere la chiave "claim", che corrisponde all’affermazione estratta (con tutte le coreferenze risolte).
DEVI rispondere SOLO nel formato descritto qui sotto. NON AGGIUNGERE ALCUNA NOTA EXTRA CHE VIOLI IL FORMATO DI RISPOSTA. INIZIA LA TUA RISPOSTA CON '['.
[formato di risposta]: 
[
    {{
    "claim": "Assicurati che l'affermazione contenga meno di 15 parole e trasmetta un'idea completa. Risolvi qualsiasi coreferenza (pronomi o altre espressioni di riferimento) nell'affermazione per chiarezza",
    }},
    ...
]

Ecco due esempi:
[testo]: Tomas Berdych ha sconfitto Gael Monfis 6-1, 6-4 sabato. Il sesto testa di serie raggiunge per la prima volta la finale del Monte Carlo Masters. Berdych affronterà Rafael Nadal o Novak Djokovic in finale.
[risposta]: [{{"claim": "Tomas Berdych ha sconfitto Gael Monfis 6-1, 6-4"}}, {{"claim": "Tomas Berdych ha sconfitto Gael Monfis 6-1, 6-4 sabato"}}, {{"claim": "Tomas Berdych raggiunge la finale del Monte Carlo Masters"}}, {{"claim": "Tomas Berdych è il sesto testa di serie"}}, {{"claim": "Tomas Berdych raggiunge la finale del Monte Carlo Masters per la prima volta"}}, {{"claim": "Tomas Berdych affronterà Rafael Nadal o Novak Djokovic"}}, {{"claim": "Tomas Berdych affronterà Rafael Nadal o Novak Djokovic in finale"}}]

[testo]: Tinder mostra solo le ultime 34 foto, ma gli utenti possono facilmente vederne di più. L’azienda ha anche dichiarato di aver migliorato la funzione degli amici in comune.
[risposta]: [{{"claim": "Tinder mostra solo le ultime foto"}}, {{"claim": "Tinder mostra solo le ultime 34 foto"}}, {{"claim": "Gli utenti di Tinder possono facilmente vedere più foto"}}, {{"claim": "Tinder ha dichiarato di aver migliorato una funzione"}}, {{"claim": "Tinder ha dichiarato di aver migliorato la funzione degli amici in comune"}}]

Ora completa il seguente compito, RISPONDI SOLO IN FORMATO LISTA, NESSUNA ALTRA PAROLA!!!:
[testo]: {input}
[risposta]: 
"""
}

QUERY_GENERATION_PROMPT = {
    "system": "Sei un generatore di query che crea ricerche efficaci e concise per verificare un'affermazione. Devi rispondere solo in formato lista Python (NESSUN’ALTRA PAROLA!)",
    "user": """Sei un generatore di query progettato per aiutare gli utenti a verificare un'affermazione utilizzando i motori di ricerca. Il tuo compito principale è generare una lista Python di due query di ricerca efficaci e scettiche. Queste query devono aiutare gli utenti a valutare criticamente la veridicità di un’affermazione fornita usando i motori di ricerca.
Devi rispondere solo nel formato descritto qui sotto (una lista Python di query). SEGUI RIGOROSAMENTE IL FORMATO. NON RESTITUIRE NIENT’ALTRO. INIZIA LA TUA RISPOSTA CON '['.
[formato di risposta]: ['query1', 'query2']

Ecco tre esempi:
affermazione: Il CEO di Twitter è Bill Gates.
risposta: ["Chi è il CEO di Twitter?", "CEO Twitter"]

affermazione: Michael Phelps è l’olimpionico più decorato di tutti i tempi.
risposta: ["Chi è l’olimpionico più decorato di tutti i tempi?", "Michael Phelps"]

affermazione: ChatGPT è stato creato da Google.
risposta: ["Chi ha creato ChatGPT?", "ChatGPT"]

Ora completa il seguente compito (RISPONDI SOLO IN FORMATO LISTA, NON RESTITUIRE ALTRE PAROLE!!! INIZIA LA TUA RISPOSTA CON '[' E TERMINA CON ']'):
affermazione: {input}
risposta: 
"""
}

VERIFICATION_PROMPT = {
    "system": "Sei un assistente brillante.",
    "user": """Ti viene fornito un testo. Il tuo compito è identificare se nel testo sono presenti errori fattuali.
Quando valuti la veridicità del testo fornito, puoi fare riferimento alle prove fornite, se necessario. Le prove possono essere utili. Alcune prove potrebbero contraddirsi tra loro. Devi prestare attenzione quando le utilizzi per giudicare la veridicità del testo.
La risposta deve essere un dizionario con quattro chiavi: "reasoning", "factuality", "error" e "correction", che corrispondono rispettivamente al ragionamento, al fatto che il testo sia fattuale o meno (Booleano - True o False), all’errore fattuale presente nel testo e al testo corretto.
Il testo fornito è il seguente
[testo]: {claim}
Le prove fornite sono le seguenti
[prove]: {evidence}
Devi rispondere solo nel formato descritto qui sotto. NON RESTITUIRE NIENT’ALTRO. INIZIA LA TUA RISPOSTA CON '{{'.
[formato di risposta]: 
{{
    "reasoning": "Perché il testo fornito è fattuale o non fattuale? Sii prudente quando dici che qualcosa non è fattuale. Quando affermi che qualcosa non è fattuale, devi fornire più prove a sostegno della tua decisione.",
    "error": "None se il testo è fattuale; altrimenti, descrivi l'errore.",
    "correction": "Il testo corretto, se c’è un errore.",
    "factuality": True se il testo è fattuale, False altrimenti.
}}
"""
}


ITALIAN_TO_ENGLISH_TRANSLATION_PROMPT = {
    "system": "You are a helpful assistant.",
    "user": """You are given a piece of text in Italian. Your task is to translate it into English. The translation should be accurate and maintain the original meaning of the text. Please ensure that the translation is grammatically correct and coherent in English.
DO NOT RESPOND WITH ANYTHING ELSE. ADDING ANY OTHER EXTRA NOTES THAT VIOLATE THE RESPONSE FORMAT IS BANNED. 

{input}
""",
}

ENGLISH_TO_ITALIAN_TRANSLATION_PROMPT = {
    "system": "You are a helpful assistant.",
    "user": """You are given a piece of text in English. Your task is to translate it into Italian. The translation should be accurate and maintain the original meaning of the text. Please ensure that the translation is grammatically correct and coherent in Italian.
DO NOT RESPOND WITH ANYTHING ELSE. ADDING ANY OTHER EXTRA NOTES THAT VIOLATE THE RESPONSE FORMAT IS BANNED.

{input}
""",
}
