#!/usr/bin/env python3
"""Focused tests for the Relationship Ontology validator."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.validate_relationship_ontology import RelationshipValidator, fixture_report, ontology_report


ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "ontology/relationship_ontology/v1.0"
REGISTRY = ROOT / "ontology/releases/v1.1-rc2/canonical_entity_registry.json"


class TestRelationshipValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = RelationshipValidator(RELEASE, REGISTRY)

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(self.validator.schema)

    def test_ontology_self_test_passes(self):
        report = ontology_report(self.validator)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(report["registered_relationship_type_count"], 20)
        self.assertEqual(report["relationship_rule_count"], 20)

    def test_all_valid_fixtures_pass(self):
        records = json.loads((RELEASE / "examples/valid_relationships.json").read_text(encoding="utf-8"))["relationships"]
        for record in records:
            with self.subTest(relationship_id=record["relationship_id"]):
                self.assertEqual(self.validator.validate_collection([record]), [])

    def test_all_invalid_fixtures_emit_expected_codes(self):
        report = fixture_report(self.validator)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["invalid_cases"]["executed"], 67)
        self.assertEqual(report["invalid_cases"]["failed"], 0)

    def test_related_to_and_virtual_inverse_are_rejected(self):
        base = json.loads((RELEASE / "examples/valid_relationships.json").read_text(encoding="utf-8"))["relationships"][0]
        for predicate, expected in (("RELATED_TO", "UNKNOWN_RELATIONSHIP_TYPE"), ("HAS_SUBTYPE", "VIRTUAL_INVERSE_MATERIALIZATION_FORBIDDEN")):
            record = dict(base, relationship_type=predicate)
            codes = {item["code"] for item in self.validator.validate_collection([record])}
            self.assertIn(expected, codes)

    def test_production_rejects_unapproved_fixture(self):
        record = json.loads((RELEASE / "examples/valid_relationships.json").read_text(encoding="utf-8"))["relationships"][0]
        codes = {item["code"] for item in self.validator.validate_collection([record], production=True)}
        self.assertIn("PRODUCTION_APPROVAL_REQUIRED", codes)

    def test_cli_outputs_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first.json"
            second = Path(temp) / "second.json"
            command = [sys.executable, str(ROOT / "scripts/validate_relationship_ontology.py"), "ontology"]
            for output in (first, second):
                result = subprocess.run(command + ["--output", str(output)], cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
