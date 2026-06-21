import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
PY=sys.executable

class TestCompatibilityPhase10And11(unittest.TestCase):
 def test_01_current_phase10_is_blocked(self):
  r=subprocess.run([PY,str(ROOT/"scripts/build_phase10_compatibility_release.py")],cwd=ROOT)
  self.assertEqual(r.returncode,2)
  report=json.loads((ROOT/"CompatibilityLayer/releases/v1.0/phase10_release_readiness.json").read_text(encoding="utf-8"))
  self.assertEqual(report["status"],"BLOCKED");self.assertEqual(report["pending_decision_count"],11);self.assertFalse(report["production_import_allowed"])
 def test_02_current_phase11_is_blocked(self):
  r=subprocess.run([PY,str(ROOT/"scripts/build_phase11_neo4j_package.py")],cwd=ROOT)
  self.assertEqual(r.returncode,2)
  report=json.loads((ROOT/"neo4j/import/compatibility-v1.0/phase11_readiness.json").read_text(encoding="utf-8"))
  self.assertEqual(report["status"],"BLOCKED");self.assertFalse(report["live_database_modified"])
 def test_03_future_approved_flow_builds_without_database_access(self):
  with tempfile.TemporaryDirectory() as td:
   tmp=Path(td); decisions=json.loads((ROOT/"CompatibilityLayer/reviews/phase9/compatibility_rule_review_decisions.json").read_text(encoding="utf-8"))
   for i,d in enumerate(decisions["decisions"]):
    if i==0:
     d.update(recommended_decision="approve",approval_status="approved",approved_by="test-reviewer",approval_date="2026-06-21T12:00:00+05:30",review_notes="Authoritative evidence and semantics reviewed for test fixture.")
    else:d.update(recommended_decision="reject",approval_status="rejected",review_notes="Rejected test fixture decision.")
   dp=tmp/"decisions.json";dp.write_text(json.dumps(decisions),encoding="utf-8");rel=tmp/"release";pkg=tmp/"neo4j"
   r=subprocess.run([PY,str(ROOT/"scripts/build_phase10_compatibility_release.py"),"--decisions",str(dp),"--output-dir",str(rel)],cwd=ROOT)
   self.assertEqual(r.returncode,0)
   manifest=json.loads((rel/"release_manifest.json").read_text(encoding="utf-8"));self.assertEqual(manifest["status"],"APPROVED");self.assertEqual(manifest["rule_count"],1)
   r=subprocess.run([PY,str(ROOT/"scripts/build_phase11_neo4j_package.py"),"--release-dir",str(rel),"--output-dir",str(pkg)],cwd=ROOT)
   self.assertEqual(r.returncode,0)
   package=json.loads((pkg/"import_manifest.json").read_text(encoding="utf-8"));self.assertEqual(package["status"],"READY_FOR_CONTROLLED_IMPORT");self.assertEqual(package["rule_count"],1);self.assertFalse(package["live_database_modified"])
   self.assertTrue((pkg/"compatibility_rules.csv").exists());self.assertTrue((pkg/"import_compatibility_rules.cypher").exists())

if __name__=="__main__":unittest.main()
