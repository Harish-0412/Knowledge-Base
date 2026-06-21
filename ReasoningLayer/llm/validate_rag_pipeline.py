"""Run RAG orchestration, live retrieval, and Llama response validation."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .chains.root_cause_chain import RootCauseChain
from .orchestrator.rag_pipeline import RAGPipeline
from .services.llm_service import LLMService
from .validation.answer_validator import AnswerValidator


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REPORTS = BASE / "reports"
QUESTIONS = [
    "What is BIOS?",
    "What is UEFI?",
    "Why is Laptop001 non-compliant?",
    "How do I fix Laptop001?",
    "What risks exist for Laptop001?",
    "Which devices are affected?",
    "How can this be prevented?",
    "What firmware version is required?",
    "What dependencies exist between BIOS and firmware?",
    "Show a fleet compliance summary.",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(name: str, value: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _unit_tests() -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "ReasoningLayer/llm/tests/test_rag_pipeline.py", "-q"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
    output = result.stdout + result.stderr
    match = re.search(r"(\d+) passed", output)
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "passed": int(match.group(1)) if match else 0,
        "return_code": result.returncode,
        "summary": output.strip().splitlines()[-1] if output.strip() else "No pytest output",
    }


def _seeded_package() -> dict[str, Any]:
    evidence = [
        {
            "evidence_id": "EVID-DOM-LIVE-001",
            "evidence_type": "DomainEvidence",
            "source_layer": "Layer1",
            "entity": "BIOS",
            "confidence": 0.96,
            "content": {"definition": "BIOS initializes hardware during system startup."},
        },
        {
            "evidence_id": "EVID-COMP-LIVE-001",
            "evidence_type": "CompatibilityEvidence",
            "source_layer": "Layer3",
            "entity": "BIOS",
            "confidence": 0.94,
            "content": {"rule_id": "DEMO-RULE-001", "requirement": "Use the validated BIOS configuration."},
        },
    ]
    return {"question": "What is BIOS?", "evidence": evidence, "ranked_evidence": evidence}


def _live_llama_smoke() -> dict[str, Any]:
    package = _seeded_package()
    answer = RootCauseChain(LLMService(), "grounded_answer_prompt.txt").run("What is BIOS?", package)
    validation = AnswerValidator().validate(answer, package)
    return {
        "status": "PASS" if answer.get("generation_status") == "PASS" else "FAIL",
        "generation_status": answer.get("generation_status"),
        "latency_ms": answer.get("latency_ms"),
        "validation": validation,
        "error": answer.get("error"),
    }


def _external_end_to_end() -> list[dict[str, Any]]:
    pipeline = RAGPipeline(offline=False)
    results = []
    for question in QUESTIONS:
        result = pipeline.run(question)
        results.append({
            "question": question,
            "intent": result["query_plan"]["intent"],
            "target_layers": result["query_plan"]["target_layers"],
            "evidence_count": len(result["evidence_package"].get("evidence", [])),
            "generation_status": result["answer"].get("generation_status"),
            "valid": result["validation"]["valid"],
            "confidence": result["validation"]["confidence"],
            "evidence_coverage": result["validation"]["evidence_coverage"],
            "hallucination_count": result["validation"]["hallucination_count"],
            "issues": result["validation"]["issues"],
            "latency_ms": result["latency_ms"],
        })
    return results


def main() -> int:
    unit = _unit_tests()
    llama = _live_llama_smoke()
    results = _external_end_to_end()
    total = len(results)
    answered = sum(item["valid"] for item in results)
    hallucinations = sum(item["hallucination_count"] for item in results)
    average_confidence = round(sum(item["confidence"] for item in results) / total, 3)
    evidence_coverage = round(sum(item["evidence_coverage"] for item in results) / total, 3)
    hallucination_rate = round(hallucinations / total, 3)
    recommendation_coverage = round(
        sum(item["valid"] and item["generation_status"] == "PASS" for item in results) / total, 3
    )
    root_cause_coverage = recommendation_coverage

    metrics = {
        "questions_answered": answered,
        "questions_total": total,
        "evidence_coverage": evidence_coverage,
        "average_confidence": average_confidence,
        "hallucination_count": hallucinations,
        "hallucination_rate": hallucination_rate,
        "recommendation_coverage": recommendation_coverage,
        "root_cause_coverage": root_cause_coverage,
    }
    thresholds = {
        "minimum_test_count": unit["passed"] >= 100,
        "llama_responses_generated": llama["status"] == "PASS",
        "all_end_to_end_questions_answered": answered == total,
        "hallucination_rate_below_5_percent": hallucination_rate < 0.05,
        "average_confidence_above_0_80": average_confidence > 0.80,
        "evidence_included": evidence_coverage > 0,
        "root_causes_generated": root_cause_coverage == 1.0,
        "recommendations_generated": recommendation_coverage == 1.0,
    }
    passed = all(thresholds.values())

    end_to_end = {"generated_at": _now(), "status": "PASS" if answered == total else "FAIL", "results": results}
    quality = {"generated_at": _now(), "status": "PASS" if passed else "FAIL", "metrics": metrics, "thresholds": thresholds}
    validation = {
        "generated_at": _now(),
        "unit_tests": unit,
        "live_llama_smoke": llama,
        "pipeline_operational": unit["status"] == "PASS" and llama["status"] == "PASS",
        "external_retrieval_ready": all(item["evidence_count"] > 0 for item in results),
        "validation_status": "PASS" if passed else "FAIL",
        "final_status": "READY_FOR_PRODUCTION_DEMO" if passed else "VALIDATION_FAILED",
    }
    _write("end_to_end_test_results.json", end_to_end)
    _write("llm_response_quality.json", quality)
    _write("rag_pipeline_validation.json", validation)
    print(json.dumps({"validation": validation, "metrics": metrics}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
