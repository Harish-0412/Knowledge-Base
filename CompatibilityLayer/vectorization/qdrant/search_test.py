import math
import os

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from sentence_transformers import SentenceTransformer

from qdrant_common import (
    COLLECTION_NAME,
    MODEL_NAME,
    REPORTS_DIR,
    TESTS_DIR,
    get_client,
    read_json,
    utc_now,
    write_json,
    write_readiness_report,
)


TOP_K = 5
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def main():
    tests = read_json(TESTS_DIR / "retrieval_tests.json")
    model = SentenceTransformer(MODEL_NAME)
    query_vectors = model.encode(
        [QUERY_INSTRUCTION + test["query"] for test in tests],
        batch_size=8,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    client = get_client()
    test_results = []
    all_scores = []
    empty_count = 0
    for test, vector in zip(tests, query_vectors):
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector.tolist(),
            limit=TOP_K,
            with_payload=True,
            with_vectors=False,
        )
        results = [
            {
                "rank": rank,
                "score": float(point.score),
                "document_id": point.payload.get("document_id"),
                "rule_id": point.payload.get("rule_id"),
                "rule_type": point.payload.get("rule_type"),
                "subject": point.payload.get("subject"),
                "object": point.payload.get("object"),
            }
            for rank, point in enumerate(response.points, start=1)
        ]
        scores = [result["score"] for result in results]
        all_scores.extend(scores)
        if not results:
            empty_count += 1
        test_results.append(
            {
                "test_id": test["test_id"],
                "query": test["query"],
                "result_count": len(results),
                "results": results,
            }
        )

    query_count = len(tests)
    average_results = sum(result["result_count"] for result in test_results) / query_count if query_count else 0
    average_score = sum(all_scores) / len(all_scores) if all_scores else 0
    valid_scores = all(math.isfinite(score) for score in all_scores)
    ready = query_count >= 15 and empty_count == 0 and valid_scores and average_results > 0
    results_report = {
        "collection_name": COLLECTION_NAME,
        "model_used": MODEL_NAME,
        "top_k": TOP_K,
        "query_count": query_count,
        "tests": test_results,
        "generated_at": utc_now(),
    }
    quality_report = {
        "query_count": query_count,
        "average_results_returned": round(average_results, 4),
        "empty_result_count": empty_count,
        "average_similarity_score": round(average_score, 6),
        "retrieval_success_rate": round((query_count - empty_count) / query_count * 100, 2) if query_count else 0,
        "scores_valid": valid_scores,
        "status": "READY" if ready else "RETRIEVAL_FAILED",
        "checked_at": utc_now(),
    }
    write_json(REPORTS_DIR / "search_test_results.json", results_report)
    write_json(REPORTS_DIR / "retrieval_quality_report.json", quality_report)
    readiness = write_readiness_report()
    if not ready:
        raise RuntimeError("Retrieval quality validation failed")
    print(f"Executed {query_count} queries; average similarity {average_score:.6f}")
    print(f"Readiness: {readiness['status']}")


if __name__ == "__main__":
    main()
