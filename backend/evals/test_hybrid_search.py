from app.services.hybrid_retrieval_service import search_hybrid_chunks


DOCUMENT_ID = "ac359318-87ed-4963-bbd1-021c2019a285"


def test_query(question: str):
    print("\n" + "=" * 60)
    print(f"QUESTION: {question}")
    print("=" * 60)

    results = search_hybrid_chunks(
        query=question,
        document_id=DOCUMENT_ID,
        limit=3,
        candidate_limit=10,
    )

    for rank, chunk in enumerate(results, start=1):
        print(
            f"\nRank {rank} | "
            f"Page {chunk['page_number']} | "
            f"Chunk {chunk['chunk_index']} | "
            f"RRF Score {chunk['rrf_score']:.6f}"
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
