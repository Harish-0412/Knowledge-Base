"""Detect unsupported claims and references in grounded RAG answers."""
from __future__ import annotations

import json
import re
from typing import Any

from ReasoningLayer.llm.validation.citation_builder import CitationBuilder


class HallucinationDetector:
    IDENTIFIER_PATTERN = re.compile(
        r"\b(?:Laptop|Device|Server|Rule|CR-)[-_]?[A-Za-z0-9.-]+\b|\bv?\d+\.\d+(?:\.\d+)?\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.citations = CitationBuilder()

    def detect(
        self,
        answer: dict[str, Any],
        evidence_package: dict[str, Any],
        question: str = "",
    ) -> dict[str, Any]:
        issues: list[str] = []
        expected = {item["citation"] for item in self.citations.build(evidence_package)}
        answer_text = " ".join(
            str(answer.get(field, ""))
            for field in ("root_cause", "impact", "recommendation", "prevention")
        )
        substantive_answer = any(
            str(answer.get(field, "")).strip()
            and "insufficient evidence" not in str(answer.get(field, "")).lower()
            for field in ("root_cause", "impact", "recommendation", "prevention")
        )
        sources = {str(source) for source in answer.get("evidence_sources", [])}
        unknown_citations = sorted(source for source in sources if source not in expected)

        if substantive_answer and not any(citation in answer_text or citation in sources for citation in expected):
            issues.append("missing citations")
        if unknown_citations:
            issues.append(f"unknown evidence references: {unknown_citations}")

        recommendation = str(answer.get("recommendation", ""))
        if recommendation and "insufficient evidence" not in recommendation.lower():
            if not any(citation in recommendation for citation in expected):
                issues.append("recommendation unsupported")

        compatibility_claim = any(
            token in answer_text.lower()
            for token in ("compatible", "incompatible", "requires", "required version", "dependency")
        )
        compatibility_citations = {
            item["citation"]
            for item in self.citations.build(evidence_package)
            if item["type"] == "Compatibility Rule"
        }
        if compatibility_claim and not any(citation in answer_text for citation in compatibility_citations):
            issues.append("compatibility claim unsupported")

        evidence_text = json.dumps(evidence_package, ensure_ascii=True).lower() + " " + question.lower()
        unknown_entities = sorted(
            {match.group(0) for match in self.IDENTIFIER_PATTERN.finditer(answer_text)}
            - {match.group(0) for match in self.IDENTIFIER_PATTERN.finditer(evidence_text)}
        )
        if unknown_entities:
            issues.append(f"unknown entities introduced: {unknown_entities}")

        score = 0.0
        for issue in issues:
            if issue == "missing citations":
                score += 0.30
            elif issue == "recommendation unsupported":
                score += 0.25
            elif issue == "compatibility claim unsupported":
                score += 0.20
            elif issue.startswith("unknown entities"):
                score += 0.15
            else:
                score += 0.20
        score = round(min(1.0, score), 3)
        return {
            "hallucination_detected": bool(issues),
            "hallucination_score": score,
            "issues": issues,
        }
