from app.services.embedding_service import create_embedding
from app.services.database_service import (
    search_similar_chunks,
    search_chunks_by_keyword,
)


RRF_K = 60

VECTOR_WEIGHT = 1.0
KEYWORD_WEIGHT = 1.5


def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    limit: int = 3,
):
    scores = {}
    chunks_by_id = {}

    for rank, chunk in enumerate(vector_results, start=1):
        chunk_id = chunk["id"]

        scores[chunk_id] = (
            scores.get(chunk_id, 0)
            + VECTOR_WEIGHT / (RRF_K + rank)
        )

        chunks_by_id[chunk_id] = chunk

    for rank, chunk in enumerate(keyword_results, start=1):
        chunk_id = chunk["id"]

        scores[chunk_id] = (
            scores.get(chunk_id, 0)
            + KEYWORD_WEIGHT / (RRF_K + rank)
        )

        chunks_by_id[chunk_id] = chunk

    ranked_ids = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )

    results = []

    for chunk_id in ranked_ids[:limit]:
        chunk = chunks_by_id[chunk_id].copy()
        chunk["rrf_score"] = scores[chunk_id]
        results.append(chunk)

    return results


def search_hybrid_chunks(
    query: str,
    document_id: str,
    limit: int = 10,
    candidate_limit: int = 5,
):
    query_embedding = create_embedding(query)

    vector_results = search_similar_chunks(
        query_embedding=query_embedding,
        document_id=document_id,
        limit=candidate_limit,
    )

    keyword_results = search_chunks_by_keyword(
        query=query,
        document_id=document_id,
        limit=candidate_limit,
    )

    return reciprocal_rank_fusion(
        vector_results=vector_results,
        keyword_results=keyword_results,
        limit=limit,
    )
