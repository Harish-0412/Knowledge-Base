import hashlib, json, subprocess, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
P8=ROOT/"CompatibilityLayer/validation/phase8"
def load(name): return json.loads((P8/name).read_text(encoding="utf-8"))
class TestCompatibilityPhase8(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.report=load("phase8_validation_report.json"); cls.results=load("phase8_candidate_validation.json"); cls.schema=load("phase8_schema_validation.json"); cls.lineage=load("phase8_lineage_validation.json")
 def test_01_status(self): self.assertEqual(self.report["status"],"PASSED_WITH_WARNINGS")
 def test_02_no_errors(self): self.assertEqual(self.report["structural_error_count"],0)
 def test_03_all_rules_pass(self): self.assertEqual(self.report["passed_rule_count"],self.report["generated_rule_count"])
 def test_04_no_failed_rules(self): self.assertEqual(self.report["failed_rule_count"],0)
 def test_05_schema_passes(self): self.assertEqual(self.schema["status"],"PASS")
 def test_06_lineage_passes(self): self.assertEqual(self.lineage["status"],"PASS")
 def test_07_all_sources_accounted(self): self.assertEqual(self.lineage["source_candidate_count"],self.lineage["accounted_source_candidate_count"])
 def test_08_trace_complete(self): self.assertTrue(self.lineage["all_generated_rules_traced"])
 def test_09_no_production_import(self): self.assertFalse(self.report["production_import_allowed"])
 def test_10_phase9_allowed(self): self.assertTrue(self.report["phase9_allowed"])
 def test_11_dry_run_non_mutating(self):
  p=P8/"phase8_validation_report.json"; before=hashlib.sha256(p.read_bytes()).hexdigest(); result=subprocess.run([sys.executable,str(ROOT/"scripts/validate_compatibility_rules.py"),"--dry-run"],cwd=ROOT); self.assertEqual(result.returncode,0); self.assertEqual(before,hashlib.sha256(p.read_bytes()).hexdigest())
