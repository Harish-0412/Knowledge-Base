import csv
import json
import unittest
from collections import Counter
from pathlib import Path


class V11RC2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent.parent
        cls.release = cls.root / "ontology/releases/v1.1-rc2"
        cls.neo4j = cls.root / "neo4j/import/v1.1-rc2"
        cls.registry = json.loads((cls.release / "canonical_entity_registry.json").read_text(encoding="utf-8"))
        cls.cross = json.loads((cls.release / "validation/cross_reference_validation.json").read_text(encoding="utf-8"))

    def test_entity_count_and_identity(self):
        self.assertEqual(self.registry["entity_count"], 54)
        entities = {e["entity_id"]: e for e in self.registry["entities"]}
        self.assertEqual(entities["MGT-009"]["canonical_name"], "Configuration Baseline")
        self.assertEqual(entities["MGT-010"]["canonical_name"], "Endpoint Agent")

    def test_new_entity_metadata_and_types(self):
        source = json.loads((self.root / "Domain_layer/working/v1.1/management.json").read_text(encoding="utf-8"))
        entities = {e["entity_id"]: e for e in source}
        expected = {"MGT-009": "Configuration Policy Object", "MGT-010": "Management Agent"}
        for entity_id, subtype in expected.items():
            entity = entities[entity_id]
            self.assertEqual(entity["type"], "ManagementTool")
            self.assertEqual(entity["subtype"], subtype)
            self.assertEqual(entity["verification_status"], "review_required")
            self.assertEqual(entity["provenance"], [])
            self.assertNotIn("compatibility_relevance", entity)

    def test_reference_acceptance_criteria(self):
        self.assertEqual(self.cross["human_review_references"], 0)
        self.assertEqual(self.cross["unclassified_references"], 0)
        self.assertEqual(self.cross["ambiguous_references"], 0)
        self.assertEqual(self.cross["self_reference_count"], 0)
        self.assertEqual(self.cross["core_resolution_percentage"], 100.0)

    def test_approved_override_counts(self):
        payload = json.loads((self.root / "ontology/reviews/v1.1_reference_resolution_overrides.json").read_text(encoding="utf-8"))
        decisions = payload["decisions"]
        self.assertEqual(len(decisions), 39)
        self.assertTrue(all(d["approval_status"] == "approved" for d in decisions))
        self.assertEqual(Counter(d["recommended_decision"] for d in decisions),
            Counter({"create_core_entity": 2, "external": 8, "deferred": 19, "rejected": 10}))

    def test_neo4j_counts(self):
        with (self.neo4j / "entities.csv").open(encoding="utf-8", newline="") as handle:
            nodes = list(csv.DictReader(handle))
        with (self.neo4j / "resolved_references.csv").open(encoding="utf-8", newline="") as handle:
            relationships = list(csv.DictReader(handle))
        self.assertEqual(len(nodes), 54)
        self.assertEqual(len(relationships), self.cross["resolved_references"])


if __name__ == "__main__":
    unittest.main()
