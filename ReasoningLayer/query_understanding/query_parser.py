"""Compose intent, entities, and routing into a unified query plan."""

from __future__ import annotations

try:
    from .entity_extractor import EntityExtractor
    from .intent_classifier import IntentClassifier
    from .query_router import QueryRouter
except ImportError:
    from entity_extractor import EntityExtractor
    from intent_classifier import IntentClassifier
    from query_router import QueryRouter


ACTIONS = {
    "ConceptExplanation": "ExplainConcept", "RootCauseAnalysis": "InvestigateViolation",
    "ComplianceStatus": "EvaluateCompliance", "RecommendationRequest": "GenerateRecommendation",
    "PreventionRequest": "GeneratePreventionStrategy", "RiskAssessment": "AssessRisk",
    "DependencyAnalysis": "TraverseDependencies", "CompatibilityInquiry": "EvaluateCompatibility",
    "ViolationInvestigation": "InvestigateViolation", "FleetAnalysis": "AnalyzeFleet",
    "DeviceInvestigation": "InvestigateDevice", "RuleExplanation": "ExplainRule",
    "VersionAnalysis": "EvaluateVersionConstraints", "LifecycleAnalysis": "EvaluateLifecycle",
    "UpgradeImpactAnalysis": "AssessUpgradeImpact",
}


class QueryParser:
    def __init__(self) -> None:
        self.classifier = IntentClassifier()
        self.extractor = EntityExtractor()
        self.router = QueryRouter()

    def parse(self, question: str) -> dict:
        classification = self.classifier.classify(question)
        entities = self.extractor.extract(question)
        intent_names = [item["intent"] for item in classification["intents"]] or [classification["intent"]]
        routing = self.router.route(intent_names, entities)
        return {
            "question": question, "intent": classification["intent"], "confidence": classification["confidence"],
            "intents": classification["intents"], "intent_mode": classification["mode"], "entities": entities,
            "target_layers": routing["target_layers"], "required_action": ACTIONS[classification["intent"]],
        }


def parse_query(question: str) -> dict:
    return QueryParser().parse(question)
