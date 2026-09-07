import json

from openai import OpenAI


client = OpenAI()


def rerank_chunks(
    question: str,
    chunks: list[dict],
    limit: int = 3,
) -> list[dict]:
    if not chunks:
        return []

    candidates = []

    for index, chunk in enumerate(chunks):
        candidates.append(
            {
                "index": index,
                "content": chunk["content"],
            }
        )

    response = client.responses.create(
        model="gpt-5-mini",
        input=f"""
You are a relevance reranker for a document retrieval system.

Your job is to rank document chunks by how directly they help
answer the user's question.

Important rules:
- Judge only relevance to the question.
- Prefer chunks that directly contain the answer.
- A chunk that merely discusses the same general topic should rank lower.
- Do not answer the question.
- Do not use outside knowledge.
- Do not invent information.
- Return ONLY valid JSON.
- Return the candidate indexes from most relevant to least relevant.

USER QUESTION:
{question}

CANDIDATES:
{json.dumps(candidates, ensure_ascii=False)}

Return JSON in exactly this format:

{{
    "ranking": [0, 1, 2]
}}
""",
    )

    result = json.loads(response.output_text)

    ranking = result["ranking"]

    reranked = []

    for index in ranking:
        if index < 0 or index >= len(chunks):
            continue

        chunk = chunks[index].copy()
        chunk["rerank_position"] = len(reranked) + 1

        reranked.append(chunk)

        if len(reranked) == limit:
            break

    return reranked
