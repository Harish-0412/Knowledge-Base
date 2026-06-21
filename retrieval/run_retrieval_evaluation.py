import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from answer_builder import AnswerBuilder
from search_service import SearchService


BASE_DIR = Path(__file__).resolve().parent
TESTS_PATH = BASE_DIR / "tests" / "retrieval_questions.json"
REPORTS_DIR = BASE_DIR / "reports"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def main():
    questions = json.loads(TESTS_PATH.read_text(encoding="utf-8"))
    service = SearchService()
    builder = AnswerBuilder()
    collection_status = service.verify_collections()
    answers = []
    all_scores = []
    search_failure_count = 0
    route_match_count = 0

    for test in questions:
        predicted_route = service.router.route(test["question"]).value
        if predicted_route == test["expected_route"]:
            route_match_count += 1
        response = service.search(
            test["question"],
            top_k=5,
        )
        answer = builder.build(test["question"], response)
        answer.update(
            {
                "question_id": test["question_id"],
                "category": test["category"],
                "expected_route": test["expected_route"],
            }
        )
        answers.append(answer)
        all_scores.extend(source["score"] for source in answer["retrieved_sources"])
        if response["errors"]:
            search_failure_count += 1

    question_count = len(questions)
    answered_count = sum(answer["answered"] for answer in answers)
    empty_count = question_count - answered_count
    source_covered = sum(bool(answer["retrieved_sources"]) for answer in answers)
    retrieved_count = sum(len(answer["retrieved_sources"]) for answer in answers)
    relevant_retrieved_count = sum(
        source["score"] >= 0.50
        for answer in answers
        for source in answer["retrieved_sources"]
    )
    answer_rate = answered_count / question_count * 100 if question_count else 0
    source_coverage = source_covered / question_count * 100 if question_count else 0
    average_documents = retrieved_count / question_count if question_count else 0
    average_similarity = sum(all_scores) / len(all_scores) if all_scores else 0
    relevance_rate = relevant_retrieved_count / retrieved_count * 100 if retrieved_count else 0
    routing_accuracy = route_match_count / question_count * 100 if question_count else 0
    collection_source_counts = Counter(
        source["collection"]
        for answer in answers
        for source in answer["retrieved_sources"]
    )
    layer1_retrieved = collection_source_counts.get("kb_domain_layer", 0) > 0
    layer3_retrieved = collection_source_counts.get("kb_compatibility_layer", 0) > 0
    missing_collections = [name for name, status in collection_status.items() if not status["exists"]]
    nonempty_answers_valid = all(
        bool(answer["summary"] and answer["detailed_explanation"])
        for answer in answers
    )
    sources_valid = all(bool(answer["retrieved_sources"]) for answer in answers)
    confidence_valid = all(
        math.isfinite(answer["confidence"]["score"]) for answer in answers
    )
    grounded_valid = all(answer["grounded_only"] for answer in answers)

    evaluation = {
        "questions_tested": question_count,
        "questions_answered": answered_count,
        "routing_accuracy": round(routing_accuracy, 2),
        "answer_rate": round(answer_rate, 2),
        "empty_result_count": empty_count,
        "average_retrieved_documents": round(average_documents, 4),
        "average_similarity_score": round(average_similarity, 6),
        "retrieved_source_relevance_rate": round(relevance_rate, 2),
        "source_coverage": round(source_coverage, 2),
        "search_failure_count": search_failure_count,
        "retrieved_source_counts_by_collection": dict(collection_source_counts),
        "collection_status": collection_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    failures = []
    if missing_collections:
        failures.append(f"Unavailable collections: {', '.join(missing_collections)}")
    if not layer1_retrieved:
        failures.append("No Layer 1 sources were retrieved")
    if not layer3_retrieved:
        failures.append("No Layer 3 sources were retrieved")
    if routing_accuracy < 100:
        failures.append(f"Routing accuracy {routing_accuracy:.2f}% is below 100%")
    if answer_rate < 90:
        failures.append(f"Answer rate {answer_rate:.2f}% is below 90%")
    if source_coverage < 90:
        failures.append(f"Source coverage {source_coverage:.2f}% is below 90%")
    if average_similarity <= 0.70:
        failures.append(f"Average similarity {average_similarity:.6f} is not greater than 0.70")
    if relevance_rate < 90:
        failures.append(f"Retrieved source relevance {relevance_rate:.2f}% is below 90%")
    if empty_count / question_count > 0.10:
        failures.append("More than 10% of questions have empty answers")
    if search_failure_count:
        failures.append(f"Search failures occurred for {search_failure_count} questions")
    if not all((nonempty_answers_valid, sources_valid, confidence_valid, grounded_valid)):
        failures.append("One or more answer quality checks failed")

    validation = {
        "checks": {
            "collections_available": not missing_collections,
            "layer1_knowledge_retrieved": layer1_retrieved,
            "layer3_knowledge_retrieved": layer3_retrieved,
            "routing_matches_expected_categories": routing_accuracy == 100,
            "answers_non_empty": nonempty_answers_valid,
            "sources_included": sources_valid,
            "confidence_calculated": confidence_valid,
            "grounded_without_llm": grounded_valid,
            "answer_rate_at_least_90_percent": answer_rate >= 90,
            "source_coverage_at_least_90_percent": source_coverage >= 90,
            "average_similarity_above_0_70": average_similarity > 0.70,
            "retrieved_documents_relevant": relevance_rate >= 90,
            "empty_answers_at_most_10_percent": empty_count / question_count <= 0.10,
            "no_search_failures": search_failure_count == 0,
        },
        "failures": failures,
        "status": "PASSED" if not failures else "FAILED",
        "final_status": "READY_FOR_LAYER_INTEGRATION" if not failures else "BLOCKED_COLLECTION_UNAVAILABLE" if missing_collections else "NOT_READY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(REPORTS_DIR / "retrieval_answers.json", answers)
    write_json(REPORTS_DIR / "retrieval_evaluation.json", evaluation)
    write_json(REPORTS_DIR / "retrieval_validation_report.json", validation)
    print(json.dumps({**evaluation, **{"validation_status": validation["status"], "final_status": validation["final_status"]}}, indent=2))


if __name__ == "__main__":
    main()
