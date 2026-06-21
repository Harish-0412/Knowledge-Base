"""
Evidence Aggregation Layer test suite.
All tests use offline=True — no live Qdrant or Neo4j required.
Run: python -m pytest ReasoningLayer/evidence_aggregation/tests/ -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ReasoningLayer.evidence_aggregation.models.evidence_models import (
    Evidence, EvidencePackage, EVIDENCE_TYPES,
)
from ReasoningLayer.evidence_aggregation.qdrant_retriever  import QdrantRetriever
from ReasoningLayer.evidence_aggregation.neo4j_retriever   import Neo4jRetriever
from ReasoningLayer.evidence_aggregation.evidence_collector import EvidenceCollector
from ReasoningLayer.evidence_aggregation.evidence_ranker    import EvidenceRanker
from ReasoningLayer.evidence_aggregation.evidence_graph_builder import EvidenceGraphBuilder
from ReasoningLayer.evidence_aggregation.evidence_aggregator    import EvidenceAggregator
from ReasoningLayer.evidence_aggregation.evidence_service       import EvidenceService

CASES_PATH = Path(__file__).parent / "evidence_test_cases.json"
BASE = Path(__file__).resolve().parents[1]


def _plan(question, intent, layers, entities=None):
    return {
        "question": question, "intent": intent, "confidence": 0.9,
        "intents": [{"intent": intent, "confidence": 0.9}],
        "intent_mode": "single", "entities": entities or {},
        "target_layers": layers, "required_action": "Investigate",
    }


class TestEvidenceModels(unittest.TestCase):
    def test_evidence_types_complete(self):
        self.assertEqual(len(EVIDENCE_TYPES), 9)

    def test_evidence_creation(self):
        e = Evidence("DomainEvidence","Layer1","Qdrant","BIOS",0.9,{"name":"BIOS"})
        self.assertTrue(e.evidence_id.startswith("EVID-"))
        self.assertIsNotNone(e.timestamp)

    def test_evidence_id_deterministic(self):
        e1 = Evidence("DomainEvidence","Layer1","Qdrant","BIOS",0.9,{"name":"BIOS"})
        e2 = Evidence("DomainEvidence","Layer1","Qdrant","BIOS",0.9,{"name":"BIOS"})
        self.assertEqual(e1.evidence_id, e2.evidence_id)

    def test_invalid_evidence_type(self):
        with self.assertRaises(ValueError):
            Evidence("BadType","Layer1","Qdrant","entity",0.5)

    def test_invalid_confidence(self):
        with self.assertRaises(ValueError):
            Evidence("DomainEvidence","Layer1","Qdrant","entity",1.5)

    def test_priority_score(self):
        e = Evidence("ViolationEvidence","Layer3","Qdrant","rule",1.0)
        e.priority = "Critical"
        self.assertEqual(e.priority_score, 100.0)

    def test_evidence_package_to_dict(self):
        pkg = EvidencePackage("QID-001","RootCauseAnalysis","Why?")
        d = pkg.to_dict()
        self.assertIn("query_id", d)
        self.assertIn("evidence", d)
        self.assertIn("ranked_evidence", d)
        self.assertIn("evidence_graph", d)


class TestQdrantRetriever(unittest.TestCase):
    def setUp(self):
        self.retriever = QdrantRetriever(offline=True)

    def test_offline_search_domain_returns_list(self):
        result = self.retriever.search_domain("BIOS")
        self.assertIsInstance(result, list)

    def test_offline_search_compatibility_returns_list(self):
        result = self.retriever.search_compatibility("firmware version")
        self.assertIsInstance(result, list)

    def test_offline_retrieve_by_entity_returns_list(self):
        result = self.retriever.retrieve_by_entity("firmware")
        self.assertIsInstance(result, list)

    def test_offline_retrieve_by_rule_returns_list(self):
        result = self.retriever.retrieve_by_rule("CRULE-FW-BIOS-001")
        self.assertIsInstance(result, list)

    def test_offline_retrieve_by_version_returns_list(self):
        result = self.retriever.retrieve_by_version("BIOS", "6.4.2")
        self.assertIsInstance(result, list)

    def test_offline_collection_exists_false(self):
        self.assertFalse(self.retriever.domain_collection_exists())
        self.assertFalse(self.retriever.compatibility_collection_exists())

    def test_operational(self):
        self.assertIsNotNone(self.retriever)


class TestNeo4jRetriever(unittest.TestCase):
    def setUp(self):
        self.retriever = Neo4jRetriever(offline=True)

    def test_offline_get_device_returns_list(self):
        result = self.retriever.get_device("Laptop001")
        self.assertIsInstance(result, list)

    def test_offline_get_firmware_returns_list(self):
        result = self.retriever.get_installed_firmware("Laptop001")
        self.assertIsInstance(result, list)

    def test_offline_get_bios_returns_list(self):
        result = self.retriever.get_installed_bios("Laptop001")
        self.assertIsInstance(result, list)

    def test_offline_get_os_returns_list(self):
        result = self.retriever.get_installed_os("Laptop001")
        self.assertIsInstance(result, list)

    def test_offline_get_drivers_returns_list(self):
        result = self.retriever.get_installed_drivers("Laptop001")
        self.assertIsInstance(result, list)

    def test_offline_get_security_agents_returns_list(self):
        result = self.retriever.get_installed_security_agents("Laptop001")
        self.assertIsInstance(result, list)

    def test_offline_get_management_agents_returns_list(self):
        result = self.retriever.get_installed_management_agents("Laptop001")
        self.assertIsInstance(result, list)

    def test_offline_not_available(self):
        self.assertFalse(self.retriever.neo4j_available)

    def test_operational(self):
        self.assertIsNotNone(self.retriever)


class TestEvidenceCollector(unittest.TestCase):
    def setUp(self):
        self.collector = EvidenceCollector(offline=True)

    def test_collect_layer1_plan(self):
        plan = _plan("What is BIOS?", "ConceptExplanation", ["Layer1"])
        result = self.collector.collect(plan)
        self.assertIsInstance(result, list)

    def test_collect_layer2_plan(self):
        plan = _plan("Why is Laptop001 failing?", "RootCauseAnalysis",
                     ["Layer2","Layer3"], {"device":"Laptop001"})
        result = self.collector.collect(plan)
        self.assertIsInstance(result, list)

    def test_collect_layer3_plan(self):
        plan = _plan("What firmware is required?", "VersionAnalysis", ["Layer3"])
        result = self.collector.collect(plan)
        self.assertIsInstance(result, list)

    def test_collect_deduplication(self):
        plan = _plan("What is BIOS?", "ConceptExplanation", ["Layer1"])
        result = self.collector.collect(plan)
        ids = [e.evidence_id for e in result]
        self.assertEqual(len(ids), len(set(ids)))

    def test_collect_hybrid_plan(self):
        plan = _plan("Why is Device001 non-compliant?", "RootCauseAnalysis",
                     ["Layer2","Layer3"], {"device":"Device001"})
        result = self.collector.collect(plan)
        self.assertIsInstance(result, list)

    def test_operational(self):
        self.assertIsNotNone(self.collector)


class TestEvidenceRanker(unittest.TestCase):
    def setUp(self):
        self.ranker = EvidenceRanker()

    def _make(self, etype, conf):
        return Evidence(etype, "Layer1", "Qdrant", "entity", conf)

    def test_violation_ranks_highest(self):
        viol = self._make("ViolationEvidence", 1.0)
        dom  = self._make("DomainEvidence",    1.0)
        ranked = self.ranker.rank([dom, viol])
        self.assertEqual(ranked[0].evidence_type, "ViolationEvidence")

    def test_risk_ranks_critical(self):
        risk = self._make("RiskEvidence", 1.0)
        dom  = self._make("DomainEvidence", 1.0)
        ranked = self.ranker.rank([dom, risk])
        self.assertEqual(ranked[0].priority, "Critical")

    def test_inventory_ranks_before_domain(self):
        inv = self._make("InventoryEvidence", 0.8)
        dom = self._make("DomainEvidence", 1.0)
        ranked = self.ranker.rank([dom, inv])
        self.assertEqual(ranked[0].evidence_type, "InventoryEvidence")

    def test_priority_assigned(self):
        e = self._make("CompatibilityEvidence", 0.9)
        ranked = self.ranker.rank([e])
        self.assertEqual(ranked[0].priority, "High")

    def test_empty_list(self):
        self.assertEqual(self.ranker.rank([]), [])

    def test_rank_descending(self):
        items = [self._make(et, 1.0) for et in [
            "DomainEvidence","InventoryEvidence","ViolationEvidence"]]
        ranked = self.ranker.rank(items)
        scores = [r.priority_score for r in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_operational(self):
        self.assertIsNotNone(self.ranker)


class TestEvidenceGraphBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = EvidenceGraphBuilder()

    def _make_with_rel(self, entity, rel, target):
        e = Evidence("CompatibilityEvidence","Layer3","Qdrant",entity,0.9)
        e.relationship = rel
        e.target = target
        return e

    def test_build_empty(self):
        g = self.builder.build([])
        self.assertEqual(g["node_count"], 0)
        self.assertEqual(g["edge_count"], 0)

    def test_build_nodes(self):
        e = Evidence("DomainEvidence","Layer1","Qdrant","BIOS",0.9)
        g = self.builder.build([e])
        self.assertEqual(g["node_count"], 1)

    def test_build_edge(self):
        e = self._make_with_rel("Laptop001","HAS_FIRMWARE","Firmware 3.2")
        g = self.builder.build([e])
        self.assertEqual(g["edge_count"], 1)
        self.assertEqual(g["edges"][0]["relationship"], "HAS_FIRMWARE")

    def test_no_duplicate_edges(self):
        e1 = self._make_with_rel("Laptop001","HAS_FIRMWARE","Firmware 3.2")
        e2 = self._make_with_rel("Laptop001","HAS_FIRMWARE","Firmware 3.2")
        g = self.builder.build([e1, e2])
        self.assertEqual(g["edge_count"], 1)

    def test_graph_has_required_keys(self):
        g = self.builder.build([])
        for key in ("node_count","edge_count","nodes","edges"):
            self.assertIn(key, g)

    def test_operational(self):
        self.assertIsNotNone(self.builder)


class TestEvidenceAggregator(unittest.TestCase):
    def setUp(self):
        self.aggregator = EvidenceAggregator(offline=True)

    def test_aggregate_returns_package(self):
        plan = _plan("What is BIOS?","ConceptExplanation",["Layer1"])
        pkg = self.aggregator.aggregate(plan)
        self.assertIsInstance(pkg, EvidencePackage)

    def test_package_has_query_id(self):
        plan = _plan("Why is Laptop001 failing?","RootCauseAnalysis",
                     ["Layer2","Layer3"],{"device":"Laptop001"})
        pkg = self.aggregator.aggregate(plan)
        self.assertTrue(pkg.query_id.startswith("QID-"))

    def test_package_intent_preserved(self):
        plan = _plan("How do I fix Device001?","RecommendationRequest",
                     ["Layer2","Layer3"],{"device":"Device001"})
        pkg = self.aggregator.aggregate(plan)
        self.assertEqual(pkg.intent, "RecommendationRequest")

    def test_package_has_evidence_graph(self):
        plan = _plan("What is BIOS?","ConceptExplanation",["Layer1"])
        pkg = self.aggregator.aggregate(plan)
        self.assertIn("nodes", pkg.evidence_graph)
        self.assertIn("edges", pkg.evidence_graph)

    def test_package_ranked_evidence_is_list(self):
        plan = _plan("What is BIOS?","ConceptExplanation",["Layer1"])
        pkg = self.aggregator.aggregate(plan)
        self.assertIsInstance(pkg.ranked_evidence, list)

    def test_package_serialisable(self):
        plan = _plan("What is BIOS?","ConceptExplanation",["Layer1"])
        pkg = self.aggregator.aggregate(plan)
        d = pkg.to_dict()
        json.dumps(d)  # must not raise

    def test_operational(self):
        self.assertIsNotNone(self.aggregator)


class TestEvidenceService(unittest.TestCase):
    def setUp(self):
        self.service = EvidenceService(offline=True)

    def test_process_string_question(self):
        pkg = self.service.process("What is BIOS?")
        self.assertIsInstance(pkg, EvidencePackage)

    def test_process_dict_plan(self):
        plan = _plan("Why is Laptop001 non-compliant?","RootCauseAnalysis",
                     ["Layer2","Layer3"],{"device":"Laptop001"})
        pkg = self.service.process(plan)
        self.assertIsInstance(pkg, EvidencePackage)

    def test_invalid_input_raises(self):
        with self.assertRaises(TypeError):
            self.service.process(12345)

    def test_end_to_end_laptop001(self):
        """Step 14: Why is Laptop001 non-compliant? must return a populated package."""
        pkg = self.service.process("Why is Laptop001 non-compliant?")
        d = pkg.to_dict()
        self.assertTrue(d["query_id"].startswith("QID-"))
        self.assertIn("evidence_graph", d)
        self.assertIsInstance(d["ranked_evidence"], list)
        self.assertIsInstance(d["evidence"], list)

    def test_operational(self):
        self.assertIsNotNone(self.service)


class TestJsonCatalogs(unittest.TestCase):
    BASE = BASE

    def _load(self, name):
        return json.loads((self.BASE / name).read_text(encoding="utf-8"))

    def test_evidence_types_count(self):
        types = self._load("evidence_types.json")
        self.assertEqual(len(types), 9)

    def test_evidence_types_have_required_fields(self):
        for t in self._load("evidence_types.json"):
            for f in ("evidence_type","description","priority"):
                self.assertIn(f, t, f"{t} missing {f}")

    def test_evidence_schema_required_fields(self):
        schema = self._load("evidence_schema.json")
        required = schema["required_fields"]
        self.assertIn("evidence_id", required)
        self.assertIn("evidence_type", required)
        self.assertIn("source_layer", required)

    def test_priority_matrix_has_rules(self):
        m = self._load("evidence_priority_matrix.json")
        self.assertGreaterEqual(len(m["rules"]), 9)
        self.assertIn("Critical", m["priority_levels"])

    def test_manifest_completeness(self):
        m = self._load("evidence_aggregation_manifest.json")
        for f in ("manifest_id","version","evidence_types","implementation_files"):
            self.assertIn(f, m)

    def test_test_corpus_count(self):
        cases = self._load("tests/evidence_test_cases.json")
        self.assertEqual(len(cases), 250)

    def test_test_corpus_distribution(self):
        cases = self._load("tests/evidence_test_cases.json")
        dist = {cat: sum(1 for c in cases if c["category"]==cat)
                for cat in ("Layer1","Layer2","Layer3","Hybrid")}
        self.assertEqual(dist, {"Layer1":50,"Layer2":50,"Layer3":50,"Hybrid":100})

    def test_test_cases_have_required_fields(self):
        cases = self._load("tests/evidence_test_cases.json")
        for c in cases:
            for f in ("test_id","category","query","expected_intent",
                      "expected_target_layers","expected_evidence_types"):
                self.assertIn(f, c, f"{c.get('test_id')} missing {f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
