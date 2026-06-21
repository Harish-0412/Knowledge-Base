"""Compute evaluation confidence from retrieval and response quality."""
from __future__ import annotations

from typing import Any


class ConfidenceEvaluator:
    def evaluate(
        self,
        evidence_package: dict[str, Any],
        validation: dict[str, Any],
        hallucination: dict[str, Any],
        answer_score: dict[str, Any],
    ) -> dict[str, float]:
        evidence = evidence_package.get("ranked_evidence") or evidence_package.get("evidence") or []
        retrieval_quality = (
            sum(float(item.get("confidence", 0.0)) for item in evidence) / len(evidence)
            if evidence else 0.0
        )
        evidence_count_score = min(1.0, len(evidence) / 3.0)
        validation_score = 1.0 if validation.get("valid") else 0.0
        hallucination_safety = 1.0 - float(hallucination.get("hallucination_score", 1.0))
        reasoning_consistency = float(answer_score.get("reasoning_score", 0.0))
        confidence = (
            0.25 * retrieval_quality
            + 0.15 * evidence_count_score
            + 0.25 * validation_score
            + 0.20 * hallucination_safety
            + 0.15 * reasoning_consistency
        )
        return {"confidence": round(confidence, 3)}
