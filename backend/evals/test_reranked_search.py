from app.services.hybrid_retrieval_service import search_hybrid_chunks
from app.services.reranking_service import rerank_chunks


DOCUMENT_ID = "ac359318-87ed-4963-bbd1-021c2019a285"


def test_query(question: str):
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    # Step 1:
    # Get a larger candidate set from hybrid retrieval.
    hybrid_candidates = search_hybrid_chunks(
        query=question,
        document_id=DOCUMENT_ID,
        limit=10,
        candidate_limit=10,
    )

    print("\nHYBRID CANDIDATES BEFORE RERANKING")

    for rank, chunk in enumerate(
        hybrid_candidates,
        start=1,
    ):
        print(
            f"\nRank {rank} | "
            f"Page {chunk['page_number']} | "
            f"Chunk {chunk['chunk_index']} | "
            f"RRF {chunk['rrf_score']:.6f}"
        )

        print(
            chunk["content"][:300]
            .replace("\n", " ")
        )

    # Step 2:
    # Rerank those candidates against the original question.
    reranked_results = rerank_chunks(
        question=question,
        chunks=hybrid_candidates,
        limit=3,
    )

    print("\n" + "-" * 70)
    print("FINAL RESULTS AFTER RERANKING")
    print("-" * 70)

    for rank, chunk in enumerate(
        reranked_results,
        start=1,
    ):
        print(
            f"\nRank {rank} | "
            f"Page {chunk['page_number']} | "
            f"Chunk {chunk['chunk_index']} | "
            f"Rerank Position "
            f"{chunk['rerank_position']}"
        )

        print(
            chunk["content"][:500]
            .replace("\n", " ")
        )


if __name__ == "__main__":
    test_query(
        "When should trading be avoided after the market opens?"
    )

    test_query(
        "What should a trader do instead of chasing price?"
    )
