import json
from pathlib import Path

from app.services.embedding_service import create_embedding
from app.services.database_service import search_similar_chunks
from app.services.hybrid_retrieval_service import search_hybrid_chunks
from app.services.reranking_service import rerank_chunks


DOCUMENT_ID = "ac359318-87ed-4963-bbd1-021c2019a285"
TOP_K = 3
CANDIDATE_LIMIT = 10


def load_eval_dataset():
    dataset_path = Path(__file__).parent / "eval_dataset.json"

    with open(dataset_path, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_text(text: str) -> str:
    return " ".join(
        text.lower()
        .replace("’", "'")
        .split()
    )


def calculate_metrics_for_question(
    item,
    retrieved_chunks,
):
    expected_pages = set(item["expected_pages"])

    retrieved_pages = {
        chunk["page_number"]
        for chunk in retrieved_chunks
    }

    ranked_pages = [
        chunk["page_number"]
        for chunk in retrieved_chunks
    ]

    # -------------------------
    # Page Hit / Recall
    # -------------------------

    matched_pages = expected_pages.intersection(
        retrieved_pages
    )

    passed = len(matched_pages) > 0

    recall = (
        len(matched_pages) / len(expected_pages)
        if expected_pages
        else 0
    )

    # -------------------------
    # Reciprocal Rank
    # -------------------------

    reciprocal_rank = 0

    for rank, page_number in enumerate(
        ranked_pages,
        start=1,
    ):
        if page_number in expected_pages:
            reciprocal_rank = 1 / rank
            break

    # -------------------------
    # Evidence Recall
    # -------------------------

    expected_evidence = item.get(
        "expected_evidence",
        []
    )

    retrieved_text = " ".join(
        chunk["content"]
        for chunk in retrieved_chunks
    )

    normalized_retrieved_text = normalize_text(
        retrieved_text
    )

    evidence_hits = []

    for evidence in expected_evidence:
        normalized_evidence = normalize_text(
            evidence
        )

        found = (
            normalized_evidence
            in normalized_retrieved_text
        )

        evidence_hits.append(found)

    evidence_recall = (
        sum(evidence_hits) / len(evidence_hits)
        if evidence_hits
        else None
    )

    return {
        "passed": passed,
        "recall": recall,
        "reciprocal_rank": reciprocal_rank,
        "evidence_recall": evidence_recall,
        "ranked_pages": ranked_pages,
    }


def print_question_result(
    item,
    retrieved_chunks,
    result,
):
    print(
        f"\n{item['id']}: "
        f"{item['question']}"
    )

    print(
        f"Expected pages: "
        f"{item['expected_pages']}"
    )

    print(
        f"Ranked pages: "
        f"{result['ranked_pages']}"
    )

    print(
        f"Result: "
        f"{'PASS' if result['passed'] else 'FAIL'}"
    )

    print(
        f"Reciprocal Rank: "
        f"{result['reciprocal_rank']:.3f}"
    )

    if result["evidence_recall"] is not None:
        print(
            f"Evidence Recall@{TOP_K}: "
            f"{result['evidence_recall']:.2%}"
        )

    print("\nTop retrieved chunks:")

    for rank, chunk in enumerate(
        retrieved_chunks,
        start=1,
    ):
        print(
            f"  Rank {rank} | "
            f"Page {chunk['page_number']} | "
            f"Chunk {chunk['chunk_index']}"
        )

        print(
            "    "
            + chunk["content"][:250]
            .replace("\n", " ")
        )


def run_eval(
    dataset,
    label,
    retrieval_function,
):
    print("\n")
    print("=" * 70)
    print(label)
    print("=" * 70)

    total_questions = len(dataset)

    successful_retrievals = 0
    total_recall = 0
    total_reciprocal_rank = 0

    total_evidence_recall = 0
    evidence_labeled_questions = 0

    for item in dataset:
        question = item["question"]

        retrieved_chunks = retrieval_function(
            question
        )

        result = calculate_metrics_for_question(
            item=item,
            retrieved_chunks=retrieved_chunks,
        )

        if result["passed"]:
            successful_retrievals += 1

        total_recall += result["recall"]

        total_reciprocal_rank += (
            result["reciprocal_rank"]
        )

        if result["evidence_recall"] is not None:
            total_evidence_recall += (
                result["evidence_recall"]
            )

            evidence_labeled_questions += 1

        print_question_result(
            item=item,
            retrieved_chunks=retrieved_chunks,
            result=result,
        )

    hit_rate = (
        successful_retrievals / total_questions
        if total_questions
        else 0
    )

    recall = (
        total_recall / total_questions
        if total_questions
        else 0
    )

    mrr = (
        total_reciprocal_rank / total_questions
        if total_questions
        else 0
    )

    evidence_recall = (
        total_evidence_recall
        / evidence_labeled_questions
        if evidence_labeled_questions
        else 0
    )

    metrics = {
        "hit_rate": hit_rate,
        "recall": recall,
        "mrr": mrr,
        "evidence_recall": evidence_recall,
    }

    print("\n" + "-" * 70)

    print(
        f"Questions: {total_questions}"
    )

    print(
        f"Retrieval Hit Rate@{TOP_K}: "
        f"{hit_rate:.2%}"
    )

    print(
        f"Retrieval Recall@{TOP_K}: "
        f"{recall:.2%}"
    )

    print(
        f"Mean Reciprocal Rank: "
        f"{mrr:.3f}"
    )

    print(
        f"Evidence Recall@{TOP_K}: "
        f"{evidence_recall:.2%}"
    )

    return metrics


# ============================================================
# RETRIEVAL STRATEGIES
# ============================================================

def vector_retrieval(question: str):
    query_embedding = create_embedding(
        question
    )

    return search_similar_chunks(
        query_embedding=query_embedding,
        document_id=DOCUMENT_ID,
        limit=TOP_K,
    )


def hybrid_reranked_retrieval(
    question: str,
):
    # 1. Hybrid retrieval creates a larger
    # candidate pool.
    hybrid_candidates = search_hybrid_chunks(
        query=question,
        document_id=DOCUMENT_ID,
        limit=CANDIDATE_LIMIT,
        candidate_limit=CANDIDATE_LIMIT,
    )

    # 2. Reranker selects final Top K.
    return rerank_chunks(
        question=question,
        chunks=hybrid_candidates,
        limit=TOP_K,
    )


def print_comparison(
    vector_metrics,
    hybrid_metrics,
):
    print("\n")
    print("=" * 70)
    print(
        "VECTOR BASELINE vs HYBRID + RERANKER"
    )
    print("=" * 70)

    print(
        f"{'Metric':<25}"
        f"{'Vector':>15}"
        f"{'Hybrid+Rerank':>20}"
    )

    print("-" * 60)

    print(
        f"{'Hit Rate@3':<25}"
        f"{vector_metrics['hit_rate']:>14.2%}"
        f"{hybrid_metrics['hit_rate']:>20.2%}"
    )

    print(
        f"{'Recall@3':<25}"
        f"{vector_metrics['recall']:>14.2%}"
        f"{hybrid_metrics['recall']:>20.2%}"
    )

    print(
        f"{'Evidence Recall@3':<25}"
        f"{vector_metrics['evidence_recall']:>14.2%}"
        f"{hybrid_metrics['evidence_recall']:>20.2%}"
    )

    print(
        f"{'MRR':<25}"
        f"{vector_metrics['mrr']:>15.3f}"
        f"{hybrid_metrics['mrr']:>20.3f}"
    )


def evaluate_retrieval():
    dataset = load_eval_dataset()

    vector_metrics = run_eval(
        dataset=dataset,
        label="VECTOR BASELINE",
        retrieval_function=vector_retrieval,
    )

    hybrid_metrics = run_eval(
        dataset=dataset,
        label="HYBRID + RERANKER",
        retrieval_function=hybrid_reranked_retrieval,
    )

    print_comparison(
        vector_metrics=vector_metrics,
        hybrid_metrics=hybrid_metrics,
    )


if __name__ == "__main__":
    evaluate_retrieval()
