"""Execute one production evaluation question through the complete RAG path."""
from __future__ import annotations

import time
from typing import Any

from ReasoningLayer.evaluation.scoring.answer_scorer import AnswerScorer
from ReasoningLayer.evaluation.scoring.confidence_evaluator import ConfidenceEvaluator
from ReasoningLayer.evaluation.scoring.hallucination_detector import HallucinationDetector
from ReasoningLayer.llm.orchestrator.rag_pipeline import RAGPipeline


class QueryExecutionEngine:
    def __init__(self, pipeline: Any | None = None) -> None:
        self.pipeline = pipeline or RAGPipeline(offline=False)
        self.hallucination_detector = HallucinationDetector()
        self.answer_scorer = AnswerScorer()
        self.confidence_evaluator = ConfidenceEvaluator()

    def execute(self, case: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            result = self.pipeline.run(case["question"])
        except Exception as exc:
            return {
                "question_id": case.get("question_id"),
                "category": case.get("category"),
                "question": case["question"],
                "intent": None,
                "expected_intent": case.get("expected_intent"),
                "intent_match": False,
                "entities": {},
                "retrieved_evidence_count": 0,
                "answer": {},
                "root_cause": "",
                "recommendation": "",
                "prevention": "",
                "confidence": 0.0,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "hallucination_score": 0.0,
                "hallucination_detected": False,
                "hallucination_issues": [],
                "validation_status": "FAIL",
                "validation_issues": [f"Execution error: {exc}"],
                "scores": {
                    "overall_score": 0.0,
                    "evidence_score": 0.0,
                    "reasoning_score": 0.0,
                    "root_cause_score": 0.0,
                    "recommendation_score": 0.0,
                    "prevention_score": 0.0,
                    "completeness_score": 0.0,
                    "consistency_score": 0.0,
                    "groundedness_score": 0.0,
                },
            }
        answer = result["answer"]
        evidence_package = result["evidence_package"]
        validation = result["validation"]
        hallucination = self.hallucination_detector.detect(answer, evidence_package, case["question"])
        scores = self.answer_scorer.score(answer, evidence_package, validation, hallucination)
        confidence = self.confidence_evaluator.evaluate(
            evidence_package, validation, hallucination, scores
        )["confidence"]
        expected_intent = case.get("expected_intent")
        intent_match = expected_intent is None or result["query_plan"]["intent"] == expected_intent
        passed = bool(validation.get("valid")) and intent_match and not hallucination["hallucination_detected"]
        return {
            "question_id": case.get("question_id"),
            "category": case.get("category"),
            "question": case["question"],
            "intent": result["query_plan"]["intent"],
            "expected_intent": expected_intent,
            "intent_match": intent_match,
            "entities": result["query_plan"].get("entities", {}),
            "retrieved_evidence_count": len(evidence_package.get("evidence", [])),
            "answer": answer,
            "root_cause": answer.get("root_cause", ""),
            "recommendation": answer.get("recommendation", ""),
            "prevention": answer.get("prevention", ""),
            "confidence": confidence,
            "latency_ms": result["latency_ms"],
            "hallucination_score": hallucination["hallucination_score"],
            "hallucination_detected": hallucination["hallucination_detected"],
            "hallucination_issues": hallucination["issues"],
            "validation_status": "PASS" if passed else "FAIL",
            "validation_issues": validation.get("issues", []),
            "scores": scores,
        }
