"""Validate required sections, citations, and evidence grounding."""
from __future__ import annotations

import re
from typing import Any

from .citation_builder import CitationBuilder


REQUIRED_FIELDS = ("root_cause", "impact", "recommendation", "prevention")
INSUFFICIENT = "insufficient evidence"


class AnswerValidator:
    def __init__(self, minimum_confidence: float = 0.80) -> None:
        self.minimum_confidence = minimum_confidence
        self.citations = CitationBuilder()

    @staticmethod
    def _text(answer: dict[str, Any]) -> str:
        return " ".join(str(answer.get(field, "")) for field in REQUIRED_FIELDS)

    def validate(self, answer: dict[str, Any], evidence_package: dict[str, Any]) -> dict[str, Any]:
        issues: list[str] = []
        expected = {item["citation"] for item in self.citations.build(evidence_package)}
        sources = {str(item) for item in answer.get("evidence_sources", [])}
        answer_text = self._text(answer)

        if not answer_text.strip():
            issues.append("Answer is empty")
        for field in REQUIRED_FIELDS:
            value = str(answer.get(field, "")).strip()
            if not value:
                issues.append(f"Missing required section: {field}")

        cited = {citation for citation in expected if citation in answer_text or citation in sources}
        unknown = sorted(source for source in sources if source not in expected)
        if not expected:
            issues.append("No evidence was retrieved")
        elif not cited:
            issues.append("Answer does not reference retrieved evidence")
        if unknown:
            issues.append(f"Unsupported evidence references: {unknown}")

        unsupported_sections = []
        for field in REQUIRED_FIELDS:
            value = str(answer.get(field, ""))
            if value and INSUFFICIENT not in value.lower() and not any(c in value for c in expected):
                unsupported_sections.append(field)
        if unsupported_sections:
            issues.append(f"Unsupported claims in sections: {unsupported_sections}")

        if INSUFFICIENT in str(answer.get("root_cause", "")).lower():
            issues.append("Root cause is not supported by evidence")
        if INSUFFICIENT in str(answer.get("recommendation", "")).lower():
            issues.append("Recommendation is not supported by evidence")

        completeness = sum(bool(str(answer.get(field, "")).strip()) for field in REQUIRED_FIELDS) / 4
        citation_coverage = len(cited) / len(expected) if expected else 0.0
        section_grounding = (4 - len(unsupported_sections)) / 4
        evidence_items = self.citations.build(evidence_package)
        evidence_confidence = (
            sum(item["confidence"] for item in evidence_items) / len(evidence_items)
            if evidence_items else 0.0
        )
        confidence = round(
            0.35 * completeness
            + 0.25 * min(1.0, citation_coverage)
            + 0.20 * section_grounding
            + 0.20 * evidence_confidence,
            3,
        )
        valid = not issues and confidence >= self.minimum_confidence
        return {
            "valid": valid,
            "confidence": confidence,
            "issues": issues,
            "hallucination_count": len(unknown) + len(unsupported_sections),
            "evidence_coverage": round(citation_coverage, 3),
        }
