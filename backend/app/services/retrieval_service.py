import numpy as np


def cosine_similarity(vector_a, vector_b):
    a = np.array(vector_a)
    b = np.array(vector_b)

    return np.dot(a, b) / (
        np.linalg.norm(a) * np.linalg.norm(b)
    )


def rank_chunks(query_embedding, chunks_with_embeddings):
    results = []

    for item in chunks_with_embeddings:
        score = cosine_similarity(
            query_embedding,
            item["embedding"],
        )

        results.append({
            "chunk_index": item["chunk_index"],
            "text": item["text"],
            "score": float(score),
        })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results
