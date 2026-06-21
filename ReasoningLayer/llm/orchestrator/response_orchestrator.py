"""Select the grounded response chain for a query-understanding intent."""
from __future__ import annotations

from typing import Any

from ..chains.recommendation_chain import RecommendationChain
from ..chains.root_cause_chain import RootCauseChain
from ..services.llm_service import LLMService


class ResponseOrchestrator:
    SUPPORTED_INTENTS = {
        "ConceptExplanation",
        "RootCauseAnalysis",
        "RecommendationRequest",
        "RiskAssessment",
        "FleetAnalysis",
        "DependencyAnalysis",
        "CompatibilityInquiry",
    }
    TEMPLATE_BY_INTENT = {
        "ConceptExplanation": "grounded_answer_prompt.txt",
        "RootCauseAnalysis": "root_cause_prompt.txt",
        "RecommendationRequest": "recommendation_prompt.txt",
        "RiskAssessment": "grounded_answer_prompt.txt",
        "FleetAnalysis": "fleet_analysis_prompt.txt",
        "DependencyAnalysis": "grounded_answer_prompt.txt",
        "CompatibilityInquiry": "grounded_answer_prompt.txt",
        "PreventionRequest": "prevention_prompt.txt",
    }

    def __init__(self, llm_service: Any | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def generate(self, question: str, evidence_package: dict[str, Any], intent: str) -> dict[str, Any]:
        template = self.TEMPLATE_BY_INTENT.get(intent, "grounded_answer_prompt.txt")
        if intent == "RecommendationRequest":
            chain = RecommendationChain(self.llm_service, template)
        else:
            chain = RootCauseChain(self.llm_service, template)
        result = chain.run(question, evidence_package)
        result["intent"] = intent
        result["chain"] = chain.__class__.__name__
        return result
