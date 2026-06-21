"""Load every evaluation dataset and execute the production RAG workflow."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .benchmark_runner import BenchmarkRunner
from .query_execution_engine import QueryExecutionEngine


BASE = Path(__file__).resolve().parents[1]
DATASETS = BASE / "datasets"
REPORTS = BASE / "reports"
DATASET_FILES = (
    "definition_questions.json",
    "compatibility_questions.json",
    "root_cause_questions.json",
    "recommendation_questions.json",
    "prevention_questions.json",
    "fleet_questions.json",
    "hybrid_questions.json",
    "stress_test_questions.json",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(name: str, value: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class EvaluationRunner:
    def __init__(self, engine: QueryExecutionEngine | None = None) -> None:
        self.engine = engine or QueryExecutionEngine()

    @staticmethod
    def load_datasets() -> list[dict[str, Any]]:
        cases = []
        for filename in DATASET_FILES:
            payload = json.loads((DATASETS / filename).read_text(encoding="utf-8"))
            cases.extend(payload["questions"])
        return cases

    @staticmethod
    def _coverage(results: list[dict[str, Any]], field: str) -> float:
        if not results:
            return 0.0
        return sum(
            bool(str(item.get(field, "")).strip())
            and "insufficient evidence" not in str(item.get(field, "")).lower()
            for item in results
        ) / len(results)

    def run(
        self,
        cases: list[dict[str, Any]] | None = None,
        limit: int | None = None,
        write_reports: bool = True,
    ) -> dict[str, Any]:
        selected = list(cases or self.load_datasets())
        if limit is not None:
            selected = selected[:limit]
        results = [self.engine.execute(case) for case in selected]
        total = len(results)
        passed = sum(item["validation_status"] == "PASS" for item in results)
        average_confidence = sum(item["confidence"] for item in results) / total if total else 0.0
        average_latency_ms = sum(item["latency_ms"] for item in results) / total if total else 0.0
        hallucination_rate = sum(item["hallucination_detected"] for item in results) / total if total else 0.0
        evidence_coverage = sum(item["scores"]["evidence_score"] for item in results) / total if total else 0.0
        retrieval_success_rate = sum(item["retrieved_evidence_count"] > 0 for item in results) / total if total else 0.0
        root_cause_coverage = self._coverage(results, "root_cause")
        recommendation_coverage = self._coverage(results, "recommendation")
        overall_score = sum(item["scores"]["overall_score"] for item in results) / total if total else 0.0
        stress = [item for item in results if item["category"] == "Stress"]
        stress_pass_rate = (
            sum(item["validation_status"] == "PASS" for item in stress) / len(stress) if stress else 0.0
        )

        metrics = {
            "total_questions": total,
            "questions_passed": passed,
            "questions_failed": total - passed,
            "average_confidence": round(average_confidence, 3),
            "average_latency_ms": round(average_latency_ms, 2),
            "average_latency_seconds": round(average_latency_ms / 1000, 3),
            "hallucination_rate": round(hallucination_rate, 3),
            "root_cause_coverage": round(root_cause_coverage, 3),
            "recommendation_coverage": round(recommendation_coverage, 3),
            "evidence_coverage": round(evidence_coverage, 3),
            "retrieval_success_rate": round(retrieval_success_rate, 3),
            "stress_benchmark_pass_rate": round(stress_pass_rate, 3),
            "overall_system_score": round(overall_score, 3),
        }
        checks = {
            "average_confidence_above_0_85": average_confidence > 0.85,
            "hallucination_rate_below_0_05": hallucination_rate < 0.05,
            "root_cause_coverage_above_0_95": root_cause_coverage > 0.95,
            "recommendation_coverage_above_0_95": recommendation_coverage > 0.95,
            "evidence_coverage_above_0_90": evidence_coverage > 0.90,
            "retrieval_success_rate_above_0_95": retrieval_success_rate > 0.95,
            "average_latency_below_5_seconds": average_latency_ms < 5000,
            "stress_benchmark_pass_rate_above_0_90": stress_pass_rate > 0.90,
        }
        ready = all(checks.values())
        benchmark = BenchmarkRunner().run(results)
        by_category = defaultdict(lambda: {"total": 0, "passed": 0})
        for item in results:
            by_category[item["category"]]["total"] += 1
            by_category[item["category"]]["passed"] += item["validation_status"] == "PASS"

        output = {
            "generated_at": _now(),
            "metrics": metrics,
            "checks": checks,
            "status": "READY_FOR_PRODUCTION_DEMO" if ready else "VALIDATION_FAILED",
            "results": results,
        }
        if write_reports:
            _write("evaluation_results.json", {"generated_at": _now(), "results": results})
            _write("evaluation_report.json", {
                "generated_at": _now(),
                "metrics": metrics,
                "category_results": dict(by_category),
                "failure_reasons": dict(Counter(issue for item in results for issue in item["validation_issues"])),
            })
            _write("benchmark_results.json", benchmark)
            _write("hallucination_report.json", {
                "generated_at": _now(),
                "hallucination_rate": round(hallucination_rate, 3),
                "flagged_answers": [item for item in results if item["hallucination_detected"]],
            })
            _write("production_readiness_report.json", {
                **metrics,
                "validation_checks": checks,
                "status": "READY_FOR_PRODUCTION_DEMO" if ready else "VALIDATION_FAILED",
                "generated_at": _now(),
            })
        return output


def main() -> int:
    result = EvaluationRunner().run()
    print(json.dumps({key: result[key] for key in ("metrics", "checks", "status")}, indent=2))
    return 0 if result["status"] == "READY_FOR_PRODUCTION_DEMO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
