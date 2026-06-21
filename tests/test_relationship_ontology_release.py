#!/usr/bin/env python3
"""Focused acceptance tests for Relationship Ontology v1.0 packaging."""

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "ontology/relationship_ontology/v1.0"


def load(name):
    return json.loads((RELEASE / name).read_text(encoding="utf-8"))


class TestRelationshipOntologyRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load("relationship_record.schema.json")
        cls.types = load("relationship_types.json")
        cls.rules = load("relationship_rules.json")
        cls.valid = load("examples/valid_relationships.json")
        cls.invalid = load("examples/invalid_relationships.json")
        cls.fixture_manifest = load("examples/example_manifest.json")
        cls.manifest = load("relationship_ontology_manifest.json")
        cls.checksums = load("artifact_checksums.json")
        cls.report = load("validation/relationship_ontology_release_validation.json")

    def test_01_required_artifacts_exist(self):
        for path in self.manifest["artifacts"]:
            self.assertTrue((ROOT / path["path"]).is_file(), path["path"])

    def test_02_schema_is_valid(self):
        Draft202012Validator.check_schema(self.schema)

    def test_03_type_and_rule_counts_align(self):
        names = [item["relationship_type"] for item in self.types["relationship_types"]]
        rule_names = [item["relationship_type"] for item in self.rules["relationship_rules"]]
        self.assertEqual(len(names), 20)
        self.assertEqual(len(rule_names), 20)
        self.assertEqual(set(names), set(rule_names))
        self.assertNotIn("RELATED_TO", names)

    def test_04_fixture_counts_and_manifest_match(self):
        self.assertGreaterEqual(len(self.valid["relationships"]), 25)
        self.assertGreaterEqual(len(self.invalid["cases"]), 64)
        self.assertEqual(self.fixture_manifest["valid_relationship_count"], len(self.valid["relationships"]))
        self.assertEqual(self.fixture_manifest["invalid_case_count"], len(self.invalid["cases"]))

    def test_05_step_6_reports_pass(self):
        self.assertEqual(load("validation/relationship_validator_self_test.json")["status"], "PASS")
        self.assertEqual(load("validation/relationship_fixture_execution.json")["status"], "PASS")

    def test_06_manifest_counts_are_derived_correctly(self):
        counts = self.manifest["counts"]
        self.assertEqual(counts["registered_relationship_types"], len(self.types["relationship_types"]))
        self.assertEqual(counts["relationship_rules"], len(self.rules["relationship_rules"]))
        self.assertEqual(counts["valid_test_relationships"], len(self.valid["relationships"]))
        self.assertEqual(counts["invalid_test_cases"], len(self.invalid["cases"]))

    def test_07_artifact_paths_are_portable_and_sorted(self):
        paths = [item["path"] for item in self.manifest["artifacts"]]
        self.assertEqual(paths, sorted(paths))
        self.assertTrue(all("\\" not in path and not Path(path).is_absolute() for path in paths))

    def test_08_checksums_match_and_are_sorted(self):
        paths = [item["path"] for item in self.checksums["artifacts"]]
        self.assertEqual(paths, sorted(paths))
        for item in self.checksums["artifacts"]:
            content = (ROOT / item["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), item["sha256"])
            self.assertEqual(len(content), item["size_bytes"])

    def test_09_no_checksum_cycles_or_temporary_files(self):
        paths = {item["path"] for item in self.checksums["artifacts"]}
        self.assertNotIn("ontology/relationship_ontology/v1.0/relationship_ontology_manifest.json", paths)
        self.assertNotIn("ontology/relationship_ontology/v1.0/artifact_checksums.json", paths)
        self.assertFalse(any("__pycache__" in path or ".pytest_cache" in path for path in paths))

    def test_10_registry_version_matches(self):
        registry = json.loads((ROOT / "ontology/releases/v1.1-rc2/canonical_entity_registry.json").read_text(encoding="utf-8"))
        self.assertEqual(self.manifest["entity_registry_version"], registry["registry_version"])

    def test_11_no_production_relationships_or_neo4j_import(self):
        scope = self.manifest["release_scope"]
        self.assertFalse(scope["contains_production_relationships"])
        self.assertFalse(scope["contains_neo4j_relationship_import"])

    def test_12_production_and_fixture_safety_policies_exist(self):
        policies = self.manifest["policies"]
        self.assertIn("approved", policies["approval_policy"])
        self.assertIn("must never be imported", policies["fixture_import_policy"])
        self.assertIn("not materialized", policies["inverse_policy"])

    def test_13_known_limitations_are_complete(self):
        text = " ".join(self.manifest["known_limitations"])
        for term in ("No production", "RELATED_TO", "evidence", "Human semantic approval", "Qdrant"):
            self.assertIn(term, text)

    def test_14_all_ten_gates_pass_for_ready(self):
        self.assertEqual(len(self.report["gates"]), 10)
        self.assertTrue(all(item["status"] == "PASS" for item in self.report["gates"]))
        self.assertEqual(self.manifest["release_status"], "READY")
        self.assertEqual(self.manifest["lifecycle_status"], "released")

    def test_15_release_notes_and_guide_exist(self):
        self.assertTrue((RELEASE / "RELEASE_NOTES.md").is_file())
        self.assertTrue((ROOT / "docs/relationship_ontology_release_guide.md").is_file())

    def test_16_verify_mode_is_non_mutating(self):
        tracked = [RELEASE / "relationship_ontology_manifest.json", RELEASE / "artifact_checksums.json", RELEASE / "validation/relationship_ontology_release_validation.json"]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked}
        result = subprocess.run([sys.executable, str(ROOT / "scripts/verify_relationship_ontology_release.py"), "verify"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked})


if __name__ == "__main__":
    unittest.main()
