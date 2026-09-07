from openai import OpenAI

client = OpenAI()


def expand_retrieval_query(question: str) -> str:
    response = client.responses.create(
        model="gpt-5-mini",
        input=f"""
You optimize search queries for a document retrieval system.

Rewrite the user's question into a concise retrieval-oriented
search query.

Rules:
- Preserve the original meaning.
- Do not answer the question.
- Do not invent facts.
- Include useful keywords and synonymous wording that may appear
  in the source document.
- Return only the rewritten search query.

USER QUESTION:
{question}
""",
    )

    return response.output_text.strip()
