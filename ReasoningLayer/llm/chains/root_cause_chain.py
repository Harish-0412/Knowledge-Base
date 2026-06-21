"""Grounded root-cause response chain."""
from __future__ import annotations

from typing import Any

from .common import GroundedChain


class RootCauseChain(GroundedChain):
    template_name = "root_cause_prompt.txt"

    def run(self, question: str, evidence_package: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        return self._call(question.strip(), evidence_package)
