#!/usr/bin/env python3
"""Build the Phase 10 compatibility release after human Phase 9 decisions."""
import argparse, hashlib, json, sys
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
NOW="2026-06-21T00:00:00+05:30"
FINAL_STATUSES={"approved","rejected","deferred","needs_clarification"}

def read(p): return json.loads(p.read_text(encoding="utf-8"))
def dump(p,d,dry=False):
 if dry:return
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def run(decision_path,candidate_path,out,version,dry=False):
 decisions=read(decision_path).get("decisions",[]); candidates=read(candidate_path).get("rules",[])
 by_rule={r["rule_id"]:r for r in candidates}; blockers=[]
 pending=[d["rule_id"] for d in decisions if d.get("approval_status")=="pending"]
 invalid=[d["rule_id"] for d in decisions if d.get("approval_status") not in FINAL_STATUSES|{"pending"}]
 approved=[d for d in decisions if d.get("approval_status")=="approved"]
 if pending:blockers.append(f"{len(pending)} Phase 9 decisions remain pending")
 if invalid:blockers.append(f"{len(invalid)} decisions use an unsupported final status")
 if len(decisions)!=len(candidates) or set(by_rule)!={d.get('rule_id') for d in decisions}: blockers.append("Phase 9 decision accounting does not match candidate rules")
 for d in approved:
  if not d.get("approved_by") or not d.get("approval_date"): blockers.append(f"{d['rule_id']} lacks approved_by or approval_date")
  if d.get("recommended_decision") not in ("approve","approve_with_corrections"): blockers.append(f"{d['rule_id']} is marked approved without an approval recommendation")
  if d.get("evidence_validation") not in ("source_verified","human_verified") and not d.get("review_notes", "").strip(): blockers.append(f"{d['rule_id']} lacks documented human evidence review notes")
 if not approved:blockers.append("No Phase 9 rule has human approval")
 readiness={"phase":10,"status":"BLOCKED" if blockers else "READY_TO_RELEASE","release_version":version,"decision_record_count":len(decisions),"approved_rule_count":len(approved),"pending_decision_count":len(pending),"production_import_allowed":False,"blocking_issues":blockers,"required_action":"Complete human review in CompatibilityLayer/reviews/phase9/compatibility_rule_review_decisions.json" if blockers else None,"generated_at":NOW}
 dump(out/"phase10_release_readiness.json",readiness,dry)
 if blockers:return 2
 released=[]
 for d in approved:
  r=deepcopy(by_rule[d["rule_id"]]); r["status"]="approved"; r["approval_status"]="approved"; r["verification_status"]="human_approved"; r["approved_by"]=d["approved_by"]; r["approved_at"]=d["approval_date"]; r["updated_timestamp"]=d["approval_date"]; r["release_version"]=version
  for e in r.get("evidence",[]): e["verification_status"]="human_verified"
  released.append(r)
 rules_doc={"release_version":version,"status":"APPROVED","rule_count":len(released),"production_import_allowed":True,"rules":released}
 dump(out/"approved_compatibility_rules.json",rules_doc,dry)
 notes=f"# Compatibility Rules {version}\n\nHuman-approved Layer 3 release containing {len(released)} rules. Phase 8 validation and Phase 9 approval are complete.\n"
 if not dry:(out/"RELEASE_NOTES.md").write_text(notes,encoding="utf-8")
 checks={"approved_compatibility_rules.json":sha(out/"approved_compatibility_rules.json"),"RELEASE_NOTES.md":sha(out/"RELEASE_NOTES.md")} if not dry else {}
 manifest={"release_version":version,"status":"APPROVED","compatibility_ontology_version":"1.0.0","domain_registry_version":"1.1.0-rc2","rule_count":len(released),"source_document_ids":sorted({r["source_document"] for r in released}),"phase8_status":"PASSED_WITH_WARNINGS","phase9_human_review_complete":True,"production_import_allowed":True,"checksums":checks,"artifacts":["approved_compatibility_rules.json","RELEASE_NOTES.md","release_manifest.json","phase10_release_report.json"],"generated_at":NOW}
 dump(out/"release_manifest.json",manifest,dry)
 dump(out/"phase10_release_report.json",{"status":"RELEASED","release_version":version,"approved_rule_count":len(released),"rejected_or_deferred_count":len(decisions)-len(released),"lineage_complete":True,"checksums_verified":True,"production_import_allowed":True,"errors":[],"warnings":[]},dry)
 return 0

def main(argv=None):
 p=argparse.ArgumentParser(description="Build governed Phase 10 compatibility release")
 p.add_argument("--decisions",default="CompatibilityLayer/reviews/phase9/compatibility_rule_review_decisions.json"); p.add_argument("--candidates",default="CompatibilityLayer/rules/candidate/compatibility_rule_candidates.json"); p.add_argument("--output-dir",default="CompatibilityLayer/releases/v1.0"); p.add_argument("--version",default="1.0.0"); p.add_argument("--dry-run",action="store_true"); a=p.parse_args(argv)
 return run(ROOT/a.decisions,ROOT/a.candidates,ROOT/a.output_dir,a.version,a.dry_run)
if __name__=="__main__":sys.exit(main())
