from openai import OpenAI

client = OpenAI()


def generate_answer(
    question: str,
    retrieved_chunks: list[dict],
    resolved_question: str | None = None,
):
    context_parts = []

    for chunk in retrieved_chunks:
        context_parts.append(
            f"""
Chunk {chunk["chunk_index"]}:
{chunk["content"]}
"""
        )

    context = "\n".join(context_parts)

    effective_question = resolved_question or question

    response = client.responses.create(
        model="gpt-5-mini",
        input=f"""
You are a document question-answering assistant.

Answer the user's question using ONLY the provided document context.

Rules:
- Do not use outside knowledge.
- You may make direct, conservative inferences when they are clearly supported by the provided context.
- Do not introduce facts, explanations, causes, or assumptions that are not supported by the context.
- If the answer cannot be supported either directly or through a clear inference from the context, say:
  "I could not find this information in the uploaded document."
- Keep the answer concise and factual.
- When making an inference, phrase it cautiously and tie it to the document context.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{effective_question}
""",
    )

    return response.output_text
