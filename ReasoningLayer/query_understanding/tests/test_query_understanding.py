"""Validate the Phase 2 query-understanding corpus and service."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
sys.path.insert(0, str(ROOT))

from ReasoningLayer.query_understanding.query_understanding_service import QueryUnderstandingService


CASES_PATH = BASE / "tests" / "query_understanding_test_cases.json"


def evaluate_cases() -> dict:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    service = QueryUnderstandingService()
    counts = {"intent": 0, "entity": 0, "routing": 0, "parsing": 0}
    failures = []
    for item in cases:
        plan = service.understand(item["query"])
        intent_ok = plan["intent"] == item["expected_intent"]
        entity_ok = all(plan["entities"].get(key) == value for key, value in item["expected_entities"].items())
        routing_ok = plan["target_layers"] == item["expected_target_layers"]
        parsing_ok = intent_ok and entity_ok and routing_ok and bool(plan["required_action"])
        counts["intent"] += intent_ok
        counts["entity"] += entity_ok
        counts["routing"] += routing_ok
        counts["parsing"] += parsing_ok
        if not parsing_ok:
            failures.append({"test_id": item["test_id"], "query": item["query"], "actual": plan,
                             "expected_intent": item["expected_intent"], "expected_entities": item["expected_entities"],
                             "expected_target_layers": item["expected_target_layers"]})
    total = len(cases)
    return {"total": total, "intent_accuracy": counts["intent"] / total, "entity_accuracy": counts["entity"] / total,
            "routing_accuracy": counts["routing"] / total, "parsing_accuracy": counts["parsing"] / total,
            "failures": failures}


class QueryUnderstandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = evaluate_cases()

    def test_required_case_count_and_distribution(self) -> None:
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 250)
        self.assertEqual({name: sum(x["category"] == name for x in cases) for name in ("Layer1", "Layer2", "Layer3", "Hybrid")},
                         {"Layer1": 50, "Layer2": 50, "Layer3": 50, "Hybrid": 100})

    def test_accuracy_thresholds(self) -> None:
        for metric in ("intent_accuracy", "entity_accuracy", "routing_accuracy", "parsing_accuracy"):
            self.assertGreater(self.results[metric], 0.90, f"{metric}: {self.results['failures'][:5]}")

    def test_catalog_and_pattern_completeness(self) -> None:
        self.assertEqual(len(json.loads((BASE / "intent_catalog.json").read_text(encoding="utf-8"))), 15)
        self.assertEqual(len(json.loads((BASE / "entity_catalog.json").read_text(encoding="utf-8"))), 15)
        self.assertGreaterEqual(len(json.loads((BASE / "query_patterns.json").read_text(encoding="utf-8"))), 150)

    def test_multi_intent_support(self) -> None:
        plan = QueryUnderstandingService().understand("Why is Device999 failing and how do I fix it?")
        self.assertEqual(plan["intent_mode"], "multi")
        self.assertIn("RootCauseAnalysis", [x["intent"] for x in plan["intents"]])
        self.assertIn("RecommendationRequest", [x["intent"] for x in plan["intents"]])

    def test_required_examples(self) -> None:
        service = QueryUnderstandingService()
        self.assertEqual(service.understand("What is BIOS?")["target_layers"], ["Layer1"])
        self.assertEqual(service.understand("Why is Laptop001 failing?")["intent"], "RootCauseAnalysis")
        self.assertEqual(service.understand("Does BIOS 2.1 support Firmware 3.2?")["entities"]["firmware"], "3.2")
        self.assertEqual(service.understand("How does BIOS affect compliance?")["target_layers"], ["Layer1", "Layer3"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
