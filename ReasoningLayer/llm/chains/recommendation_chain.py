"""Grounded immediate and long-term remediation chain."""
from __future__ import annotations

from typing import Any

from .common import GroundedChain


class RecommendationChain(GroundedChain):
    template_name = "recommendation_prompt.txt"
    RECOMMENDATION_FIELDS = ("immediate_fix", "long_term_fix", "risk_reduction", "rollback_guidance")

    def run(self, question: str, evidence_package: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        result = self._call(question.strip(), evidence_package)
        for field in self.RECOMMENDATION_FIELDS:
            result.setdefault(field, "Insufficient evidence")
        return result
