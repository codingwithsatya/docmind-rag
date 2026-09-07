from openai import OpenAI

client = OpenAI()


def rewrite_query(
    question: str,
    conversation_history: list[dict],
) -> str:
    if not conversation_history:
        return question

    history_parts = []

    for turn in conversation_history[-3:]:
        history_parts.append(
            f"""
User: {turn["question"]}
Assistant: {turn["answer"]}
"""
        )

    history = "\n".join(history_parts)

    response = client.responses.create(
        model="gpt-5-mini",
        input=f"""
You rewrite follow-up questions into standalone
search queries for a document retrieval system.

Use the conversation history only to resolve
references in the current question.

Rules:
- Preserve the user's original meaning.
- Do not answer the question.
- Do not add facts that are not present.
- Return only the rewritten search query.
- If the question is already standalone,
  return it unchanged.

CONVERSATION HISTORY:
{history}

CURRENT QUESTION:
{question}
""",
    )

    return response.output_text.strip()
