"""Score response completeness, reasoning quality, and groundedness."""
from __future__ import annotations

from typing import Any

from ReasoningLayer.llm.validation.citation_builder import CitationBuilder


class AnswerScorer:
    REQUIRED = ("root_cause", "impact", "recommendation", "prevention")

    def __init__(self) -> None:
        self.citations = CitationBuilder()

    @staticmethod
    def _usable(value: Any) -> bool:
        text = str(value or "").strip().lower()
        return bool(text) and "insufficient evidence" not in text

    def score(
        self,
        answer: dict[str, Any],
        evidence_package: dict[str, Any],
        validation: dict[str, Any],
        hallucination: dict[str, Any],
    ) -> dict[str, Any]:
        expected = {item["citation"] for item in self.citations.build(evidence_package)}
        used = {
            citation
            for citation in expected
            if citation in " ".join(str(value) for value in answer.values())
        }
        evidence_score = len(used) / len(expected) if expected else 0.0
        root_score = 1.0 if self._usable(answer.get("root_cause")) else 0.0
        recommendation_score = 1.0 if self._usable(answer.get("recommendation")) else 0.0
        prevention_score = 1.0 if self._usable(answer.get("prevention")) else 0.0
        completeness = sum(self._usable(answer.get(field)) for field in self.REQUIRED) / 4
        consistency = 1.0 if validation.get("valid") and not validation.get("issues") else 0.0
        groundedness = evidence_score * (
            1.0 - float(hallucination.get("hallucination_score", 1.0))
        )
        reasoning_score = (root_score + recommendation_score + prevention_score + consistency) / 4
        overall = (
            0.25 * evidence_score
            + 0.25 * reasoning_score
            + 0.15 * completeness
            + 0.15 * consistency
            + 0.20 * groundedness
        )
        return {
            "overall_score": round(overall, 3),
            "evidence_score": round(evidence_score, 3),
            "reasoning_score": round(reasoning_score, 3),
            "root_cause_score": round(root_score, 3),
            "recommendation_score": round(recommendation_score, 3),
            "prevention_score": round(prevention_score, 3),
            "completeness_score": round(completeness, 3),
            "consistency_score": round(consistency, 3),
            "groundedness_score": round(groundedness, 3),
        }
