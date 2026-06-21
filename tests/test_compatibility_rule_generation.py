"""Phase 7 candidate-rule generation contract tests."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "CompatibilityLayer/rules/candidate"
RULES_PATH = CAND / "compatibility_rule_candidates.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

class TestCompatibilityRuleGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = load(RULES_PATH)
        cls.rules = cls.payload["rules"]
        cls.manifest = load(CAND / "candidate_rule_manifest.json")
        cls.trace = load(CAND / "candidate_generation_trace.json")
        cls.clarification = load(ROOT / "CompatibilityLayer/rules/needs_clarification/compatibility_rules_needing_clarification.json")
        cls.registry_ids = {e["entity_id"] for e in load(ROOT / "ontology/releases/v1.1-rc2/canonical_entity_registry.json")["entities"]}

    def test_01_required_fields(self):
        required={"rule_id","source_candidate_ids","rule_type","status","subject","predicate","object","condition_logic","conditions","requirements","exceptions","remediations","evidence","confidence","source_document","created_timestamp","updated_timestamp"}
        for r in self.rules: self.assertFalse(required-set(r))
    def test_02_deterministic_id_format(self):
        for r in self.rules: self.assertRegex(r["rule_id"], r"^CRULE-[0-9A-F]{16}-[0-9]{3,}$")
    def test_03_unique_ids(self): self.assertEqual(len(self.rules),len({r["rule_id"] for r in self.rules}))
    def test_04_source_lineage(self):
        for r in self.rules: self.assertTrue(r["source_candidate_ids"])
    def test_05_subject_resolution(self):
        for r in self.rules: self.assertIn(r["subject"].get("entity_id"),self.registry_ids)
    def test_06_object_resolution(self):
        for r in self.rules: self.assertIn(r["object"].get("entity_id"),self.registry_ids)
    def test_07_no_unknown_entities(self):
        for r in self.rules:
            self.assertNotEqual(r["subject"].get("entity_name","").lower(),"unknown"); self.assertNotEqual(r["object"].get("entity_name","").lower(),"unknown")
    def test_08_condition_logic(self):
        for r in self.rules: self.assertIn(r["condition_logic"],{"AND","OR"})
    def test_09_versions_preserved(self):
        for r in self.rules:
            for x in r["conditions"]+r["requirements"]: self.assertIn("version_raw",x)
    def test_10_requirements_list(self):
        for r in self.rules: self.assertIsInstance(r["requirements"],list)
    def test_11_exceptions_list(self):
        for r in self.rules: self.assertIsInstance(r["exceptions"],list)
    def test_12_remediation_modality(self):
        for r in self.rules:
            for x in r["remediations"]: self.assertTrue(x.get("remediation_hint"))
    def test_13_evidence_lineage(self):
        for r in self.rules: self.assertTrue(r["evidence"] and r["evidence"][0].get("source_excerpt"))
    def test_14_candidate_status(self):
        for r in self.rules: self.assertEqual(r["approval_status"],"candidate")
    def test_15_review_required(self):
        for r in self.rules: self.assertEqual(r["verification_status"],"review_required")
    def test_16_rule_types(self):
        allowed={"min_version_constraint","known_issue_fixed","readiness_requirement","feature_support_added","incompatible_combination","update_order_constraint"}
        for r in self.rules: self.assertIn(r["rule_type"],allowed)
    def test_17_predicates_registered(self):
        for r in self.rules: self.assertIn(r["predicate"],{"REQUIRES","SUPPORTS","CONFLICTS_WITH","FIXED_BY","BLOCKS"})
    def test_18_no_related_to(self):
        for r in self.rules: self.assertNotEqual(r["predicate"],"RELATED_TO")
    def test_19_no_invented_ids(self):
        for r in self.rules:
            for side in ("subject","object"): self.assertIn(r[side].get("entity_id"),self.registry_ids)
    def test_20_clarification_output(self): self.assertEqual(self.clarification["source_candidate_count"],32)
    def test_21_manifest_counts(self): self.assertEqual(self.manifest["generated_rule_count"],len(self.rules))
    def test_22_trace_count(self): self.assertEqual(self.trace["total_traces"],len(self.rules))
    def test_23_import_disabled(self): self.assertFalse(self.manifest["production_import_allowed"])
    def test_24_no_neo4j_outputs(self): self.assertFalse(any("neo4j" in str(p).lower() for p in self.manifest["artifacts"]))
    def test_25_no_qdrant_outputs(self): self.assertFalse(any("qdrant" in str(p).lower() for p in self.manifest["artifacts"]))
    def test_26_dry_run_writes_nothing(self):
        before=hashlib.sha256(RULES_PATH.read_bytes()).hexdigest()
        cmd=[sys.executable,str(ROOT/"scripts/generate_compatibility_rules.py"),"--corrected-input","CompatibilityLayer/rules/corrected/corrected_rule_candidates.json","--compatibility-ontology","CompatibilityLayer/ontology","--domain-registry","ontology/releases/v1.1-rc2/canonical_entity_registry.json","--output-dir","CompatibilityLayer/rules/candidate","--clarification-dir","CompatibilityLayer/rules/needs_clarification","--dry-run"]
        self.assertEqual(subprocess.run(cmd,cwd=ROOT,capture_output=True).returncode,0)
        self.assertEqual(before,hashlib.sha256(RULES_PATH.read_bytes()).hexdigest())
    def test_27_payload_count(self): self.assertEqual(self.payload["generated_rule_count"],len(self.rules))

if __name__ == "__main__": unittest.main()
