import hashlib, json, subprocess, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
P9=ROOT/"CompatibilityLayer/reviews/phase9"
def load(name): return json.loads((P9/name).read_text(encoding="utf-8"))
class TestCompatibilityPhase9(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.report=load("phase9_review_preparation_report.json"); cls.decisions=load("compatibility_rule_review_decisions.json"); cls.clar=load("clarification_review.json"); cls.high=load("high_risk_rule_review.json"); cls.ev=load("evidence_review.json")
 def test_01_ready(self): self.assertEqual(self.report["status"],"READY_FOR_HUMAN_REVIEW")
 def test_02_one_decision_per_rule(self): self.assertEqual(self.report["generated_rule_count"],self.decisions["decision_record_count"])
 def test_03_unique_rule_decisions(self): self.assertEqual(len(self.decisions["decisions"]),len({x["rule_id"] for x in self.decisions["decisions"]}))
 def test_04_all_pending(self): self.assertTrue(all(x["approval_status"]=="pending" for x in self.decisions["decisions"]))
 def test_05_no_approvers(self): self.assertTrue(all(x["approved_by"] is None and x["approval_date"] is None for x in self.decisions["decisions"]))
 def test_06_allowed_recommendations(self): self.assertTrue(all(x["recommended_decision"] in self.decisions["allowed_decisions"] for x in self.decisions["decisions"]))
 def test_07_clarification_accounting(self): self.assertEqual(self.report["clarification_item_count"],self.clar["clarification_item_count"])
 def test_08_lineage_complete(self): self.assertTrue(self.report["lineage_complete"])
 def test_09_all_sources_accounted(self): self.assertEqual(self.report["source_candidate_count"],self.report["accounted_source_candidate_count"])
 def test_10_high_risk_pending(self): self.assertTrue(all(x["approval_status"]=="pending" for x in self.high["rules"]))
 def test_11_evidence_pending(self): self.assertTrue(all(x["review_decision"]=="pending" for x in self.ev["records"]))
 def test_12_phase10_blocked(self): self.assertFalse(self.report["phase10_allowed"])
 def test_13_workbook_exists(self): self.assertTrue((P9/"compatibility_rule_review_workbook.md").is_file())
 def test_14_dry_run_non_mutating(self):
  p=P9/"compatibility_rule_review_decisions.json"; before=hashlib.sha256(p.read_bytes()).hexdigest(); result=subprocess.run([sys.executable,str(ROOT/"scripts/prepare_phase9_compatibility_review.py"),"--dry-run"],cwd=ROOT); self.assertEqual(result.returncode,0); self.assertEqual(before,hashlib.sha256(p.read_bytes()).hexdigest())
