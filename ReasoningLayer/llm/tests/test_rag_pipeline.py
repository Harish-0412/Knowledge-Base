"""RAG orchestration contract tests with 105 categorized questions."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ReasoningLayer.llm.orchestrator.rag_pipeline import RAGPipeline
from ReasoningLayer.llm.orchestrator.response_orchestrator import ResponseOrchestrator
from ReasoningLayer.llm.validation.answer_validator import AnswerValidator


BASE = Path(__file__).resolve().parents[1]


def _questions() -> list[dict[str, str]]:
    patterns = {
        "Definitions": ("What is BIOS concept {n}?", "ConceptExplanation"),
        "Root Cause": ("Why is Laptop{n:03d} non-compliant?", "RootCauseAnalysis"),
        "Recommendations": ("How do I fix Laptop{n:03d}?", "RecommendationRequest"),
        "Risk": ("What risks exist for Laptop{n:03d}?", "RiskAssessment"),
        "Fleet Analysis": ("Show fleet risk for device group {n}.", "FleetAnalysis"),
        "Compatibility": ("Is BIOS {n}.0 compatible with firmware 3.2?", "CompatibilityInquiry"),
        "Hybrid Questions": ("Why is Laptop{n:03d} failing and how do I fix it?", "RootCauseAnalysis"),
    }
    return [
        {"id": f"RAG-{index:03d}", "category": category, "question": pattern.format(n=n), "expected_intent": intent}
        for index, (category, (pattern, intent), n) in enumerate(
            ((category, value, n) for category, value in patterns.items() for n in range(1, 16)), start=1
        )
    ]


TEST_QUESTIONS = _questions()


class FakeEvidenceService:
    def process(self, plan: dict) -> dict:
        device = plan.get("entities", {}).get("device", "Laptop001")
        evidence = [
            {
                "evidence_id": "EVID-DOM-001",
                "evidence_type": "DomainEvidence",
                "source_layer": "Layer1",
                "entity": "BIOS",
                "confidence": 0.95,
                "content": {"definition": "BIOS initializes platform hardware."},
            },
            {
                "evidence_id": "EVID-INV-001",
                "evidence_type": "InventoryEvidence",
                "source_layer": "Layer2",
                "entity": device,
                "confidence": 0.96,
                "content": {"device_id": device, "bios_version": "1.4.0"},
            },
            {
                "evidence_id": "EVID-COMP-001",
                "evidence_type": "CompatibilityEvidence",
                "source_layer": "Layer3",
                "entity": "BIOS",
                "confidence": 0.94,
                "content": {"rule_id": "CR-BIOS-17", "requirement": "BIOS 1.6.0 or newer"},
            },
        ]
        return {
            "query_id": "QID-TEST",
            "intent": plan["intent"],
            "question": plan["question"],
            "entities": [],
            "evidence": evidence,
            "ranked_evidence": evidence,
            "evidence_graph": {"nodes": [], "edges": []},
            "metadata": {"evidence_count": len(evidence)},
        }


class FakeLLMService:
    def generate_response(self, prompt: str) -> dict:
        citations = list(dict.fromkeys(re.findall(r"\[(?:Domain Evidence|Inventory Evidence|Compatibility Rule)\] EVID-[A-Z0-9-]+", prompt)))
        citation = citations[0]
        payload = {
            "root_cause": f"The retrieved configuration does not meet its rule. {citation}",
            "impact": f"The device is exposed to the recorded compliance impact. {citation}",
            "recommendation": f"Apply the remediation stated by the retrieved rule. {citation}",
            "prevention": f"Validate this rule before future configuration changes. {citation}",
            "immediate_fix": f"Apply the retrieved compatible configuration. {citation}",
            "long_term_fix": f"Continuously validate the retrieved rule. {citation}",
            "risk_reduction": f"Removes the evidenced mismatch. {citation}",
            "rollback_guidance": f"Use only the rollback state documented in evidence. {citation}",
            "evidence_sources": citations,
        }
        return {"status": "PASS", "response": json.dumps(payload), "latency_ms": 1.0, "error": None}


@pytest.fixture(scope="module")
def pipeline() -> RAGPipeline:
    orchestrator = ResponseOrchestrator(llm_service=FakeLLMService())
    return RAGPipeline(evidence_service=FakeEvidenceService(), response_orchestrator=orchestrator)


def test_corpus_has_105_questions_across_requested_categories() -> None:
    assert len(TEST_QUESTIONS) == 105
    categories = {item["category"] for item in TEST_QUESTIONS}
    assert categories == {"Definitions", "Root Cause", "Recommendations", "Risk", "Fleet Analysis", "Compatibility", "Hybrid Questions"}
    assert all(sum(item["category"] == category for item in TEST_QUESTIONS) == 15 for category in categories)


@pytest.mark.parametrize("case", TEST_QUESTIONS, ids=lambda case: case["id"])
def test_rag_question(case: dict[str, str], pipeline: RAGPipeline) -> None:
    result = pipeline.run(case["question"])
    assert result["query_plan"]["intent"] == case["expected_intent"]
    assert result["status"] == "PASS", result["validation"]
    assert result["validation"]["confidence"] > 0.80
    assert result["validation"]["hallucination_count"] == 0
    assert result["answer"]["evidence_sources"]


@pytest.mark.parametrize("name", [
    "root_cause_prompt.txt", "recommendation_prompt.txt", "prevention_prompt.txt",
    "fleet_analysis_prompt.txt", "grounded_answer_prompt.txt",
])
def test_prompt_grounding_contract(name: str) -> None:
    text = (BASE / "prompts" / name).read_text(encoding="utf-8")
    for section in ("ROLE", "TASK", "EVIDENCE", "QUESTION", "OUTPUT FORMAT", "HALLUCINATION PREVENTION RULES"):
        assert section in text
    for required in ("Root Cause", "Impact", "Recommendation", "Prevention", "Evidence Sources"):
        assert required in text


def test_validator_rejects_uncited_claims() -> None:
    package = FakeEvidenceService().process({"intent": "RootCauseAnalysis", "question": "x", "entities": {}})
    answer = {field: "Unsupported statement" for field in ("root_cause", "impact", "recommendation", "prevention")}
    answer["evidence_sources"] = []
    result = AnswerValidator().validate(answer, package)
    assert not result["valid"]
    assert result["hallucination_count"] == 4


def test_pipeline_abstains_without_evidence() -> None:
    class EmptyEvidenceService:
        def process(self, plan: dict) -> dict:
            return {"question": plan["question"], "intent": plan["intent"], "evidence": [], "ranked_evidence": []}

    pipeline = RAGPipeline(
        evidence_service=EmptyEvidenceService(),
        response_orchestrator=ResponseOrchestrator(llm_service=FakeLLMService()),
    )
    result = pipeline.run("What is BIOS?")
    assert result["answer"]["generation_status"] == "ABSTAINED"
    assert result["status"] == "FAIL"
    assert "No evidence was retrieved" in result["validation"]["issues"]
