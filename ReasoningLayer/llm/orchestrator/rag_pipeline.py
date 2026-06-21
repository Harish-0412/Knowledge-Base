"""End-to-end grounded RAG orchestration."""
from __future__ import annotations

import time
from typing import Any

from ReasoningLayer.evidence_aggregation.evidence_service import EvidenceService
from ReasoningLayer.query_understanding.query_understanding_service import QueryUnderstandingService

from ..validation.answer_validator import AnswerValidator
from .response_orchestrator import ResponseOrchestrator


class RAGPipeline:
    def __init__(
        self,
        query_service: Any | None = None,
        evidence_service: Any | None = None,
        response_orchestrator: ResponseOrchestrator | None = None,
        answer_validator: AnswerValidator | None = None,
        offline: bool = False,
    ) -> None:
        self.query_service = query_service or QueryUnderstandingService()
        self.evidence_service = evidence_service or EvidenceService(offline=offline)
        self.response_orchestrator = response_orchestrator or ResponseOrchestrator()
        self.answer_validator = answer_validator or AnswerValidator()

    def run(self, question: str) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        started = time.perf_counter()
        query_plan = self.query_service.understand(question.strip())
        package = self.evidence_service.process(query_plan)
        evidence_package = package.to_dict() if hasattr(package, "to_dict") else dict(package)
        answer = self.response_orchestrator.generate(
            question.strip(), evidence_package, query_plan["intent"]
        )
        validation = self.answer_validator.validate(answer, evidence_package)
        return {
            "question": question.strip(),
            "query_plan": query_plan,
            "evidence_package": evidence_package,
            "answer": answer,
            "validation": validation,
            "status": "PASS" if validation["valid"] else "FAIL",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }


def run_rag(question: str, offline: bool = False) -> dict[str, Any]:
    return RAGPipeline(offline=offline).run(question)
