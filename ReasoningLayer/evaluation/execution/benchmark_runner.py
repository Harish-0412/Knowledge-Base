"""Aggregate production evaluation results into category benchmarks."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BASE / "benchmarks" / "benchmark_manifest.json"


class BenchmarkRunner:
    def __init__(self, manifest_path: Path = MANIFEST_PATH) -> None:
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    @staticmethod
    def _coverage(items: list[dict[str, Any]], field: str) -> float:
        if not items:
            return 0.0
        usable = sum(
            bool(str(item.get(field, "")).strip())
            and "insufficient evidence" not in str(item.get(field, "")).lower()
            for item in items
        )
        return usable / len(items)

    def run(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        benchmarks = {}
        for benchmark in self.manifest["benchmarks"]:
            categories = set(benchmark["categories"])
            items = [item for item in results if item["category"] in categories]
            total = len(items)
            passed = sum(item["validation_status"] == "PASS" for item in items)
            benchmarks[benchmark["name"]] = {
                "questions": total,
                "accuracy": round(passed / total, 3) if total else 0.0,
                "groundedness": round(sum(item["scores"]["groundedness_score"] for item in items) / total, 3) if total else 0.0,
                "hallucination_rate": round(sum(item["hallucination_detected"] for item in items) / total, 3) if total else 0.0,
                "confidence": round(sum(item["confidence"] for item in items) / total, 3) if total else 0.0,
                "average_latency_ms": round(sum(item["latency_ms"] for item in items) / total, 2) if total else 0.0,
                "recommendation_coverage": round(self._coverage(items, "recommendation"), 3),
                "root_cause_coverage": round(self._coverage(items, "root_cause"), 3),
                "evidence_coverage": round(sum(item["retrieved_evidence_count"] > 0 for item in items) / total, 3) if total else 0.0,
            }
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "benchmarks": benchmarks}


def main() -> int:
    results_path = BASE / "reports" / "evaluation_results.json"
    report_path = BASE / "reports" / "benchmark_results.json"
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    report = BenchmarkRunner().run(payload["results"])
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
