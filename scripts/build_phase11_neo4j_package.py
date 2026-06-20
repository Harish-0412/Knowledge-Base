#!/usr/bin/env python3
"""Build a non-executing Neo4j import package from an approved Phase 10 release."""
import argparse,csv,hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
NOW="2026-06-21T00:00:00+05:30"
ALLOWED={"REQUIRES","SUPPORTS","CONFLICTS_WITH","FIXED_BY","UPGRADE_TO","DEPENDS_ON","REMEDIATES","BLOCKS","SUPERSEDES","REFERENCES","HAS_CONDITION","HAS_EXCEPTION","HAS_EVIDENCE","HAS_REMEDIATION","VALIDATED_BY","APPROVED_BY","DERIVED_FROM","REPLACES","TARGETS","SUPPORTED_BY"}
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def dump(p,d,dry=False):
 if dry:return
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csv_write(path,fields,rows,dry):
 if dry:return
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open("w",encoding="utf-8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def run(release_dir,out,dry=False):
 manifest_path=release_dir/"release_manifest.json"; blockers=[]
 if not manifest_path.exists():blockers.append("Phase 10 release manifest is missing")
 manifest=read(manifest_path) if manifest_path.exists() else {}
 if manifest.get("status")!="APPROVED" or not manifest.get("production_import_allowed"):blockers.append("Phase 10 release is not approved for production import")
 rules_path=release_dir/"approved_compatibility_rules.json"
 if not rules_path.exists():blockers.append("Approved compatibility rule artifact is missing")
 rules=read(rules_path).get("rules",[]) if rules_path.exists() else []
 if not rules:blockers.append("Approved Phase 10 release contains no rules")
 if any(r.get("predicate") not in ALLOWED for r in rules):blockers.append("Release contains a non-allowlisted predicate")
 if any(r.get("approval_status")!="approved" or not r.get("approved_by") or not r.get("approved_at") for r in rules):blockers.append("Release contains a rule without complete human approval")
 readiness={"phase":11,"status":"BLOCKED" if blockers else "READY_TO_PACKAGE","release_version":manifest.get("release_version"),"approved_rule_count":len(rules),"live_database_modified":False,"production_import_allowed":False,"blocking_issues":blockers,"required_action":"Complete Phase 9 human decisions and build Phase 10 first" if blockers else None,"generated_at":NOW}
 dump(out/"phase11_readiness.json",readiness,dry)
 if blockers:return 2
 node_rows=[];target_rows=[];by_pred={}
 for r in rules:
  node_rows.append({"rule_id:ID(CompatibilityRule)":r["rule_id"],"rule_type":r["rule_type"],"status":r["status"],"predicate":r["predicate"],"confidence:float":r["confidence"],"severity":r["severity"],"condition_logic":r["condition_logic"],"conditions_json":json.dumps(r.get("conditions",[]),sort_keys=True,separators=(",",":")),"exceptions_json":json.dumps(r.get("exceptions",[]),sort_keys=True,separators=(",",":")),"evidence_json":json.dumps(r.get("evidence",[]),sort_keys=True,separators=(",",":")),"remediations_json":json.dumps(r.get("remediations",[]),sort_keys=True,separators=(",",":")),"source_document":r["source_document"],"approved_by":r["approved_by"],"approved_at":r["approved_at"],"release_version":manifest["release_version"]})
  target_rows.append({":START_ID(CompatibilityRule)":r["rule_id"],":END_ID(Entity)":r["subject"]["entity_id"],":TYPE":"TARGETS"})
  by_pred.setdefault(r["predicate"],[]).append({":START_ID(CompatibilityRule)":r["rule_id"],":END_ID(Entity)":r["object"]["entity_id"],"rule_id":r["rule_id"],"approval_status":"approved"})
 csv_write(out/"compatibility_rules.csv",list(node_rows[0]),node_rows,dry);csv_write(out/"rule_targets.csv",list(target_rows[0]),target_rows,dry)
 for pred,rows in sorted(by_pred.items()):csv_write(out/f"approved_{pred.lower()}.csv",list(rows[0]),rows,dry)
 constraints="""CREATE CONSTRAINT compatibility_rule_id_unique IF NOT EXISTS\nFOR (rule:CompatibilityRule) REQUIRE rule.rule_id IS UNIQUE;\nCREATE INDEX compatibility_rule_type IF NOT EXISTS\nFOR (rule:CompatibilityRule) ON (rule.rule_type);\n"""
 imports=["LOAD CSV WITH HEADERS FROM 'file:///compatibility-v1.0/compatibility_rules.csv' AS row\nMERGE (r:CompatibilityRule {rule_id: row['rule_id:ID(CompatibilityRule)']})\nSET r.rule_type = row.rule_type, r.status = row.status, r.predicate = row.predicate,\n    r.confidence = toFloat(row['confidence:float']), r.severity = row.severity,\n    r.condition_logic = row.condition_logic, r.conditions_json = row.conditions_json,\n    r.exceptions_json = row.exceptions_json, r.evidence_json = row.evidence_json,\n    r.remediations_json = row.remediations_json, r.source_document = row.source_document,\n    r.approved_by = row.approved_by, r.approved_at = datetime(row.approved_at),\n    r.release_version = row.release_version;","LOAD CSV WITH HEADERS FROM 'file:///compatibility-v1.0/rule_targets.csv' AS row\nMATCH (r:CompatibilityRule {rule_id: row[':START_ID(CompatibilityRule)']})\nMATCH (e:Entity {entity_id: row[':END_ID(Entity)']})\nMERGE (r)-[:TARGETS]->(e);"]
 for pred in sorted(by_pred):imports.append(f"LOAD CSV WITH HEADERS FROM 'file:///compatibility-v1.0/approved_{pred.lower()}.csv' AS row\nMATCH (r:CompatibilityRule {{rule_id: row[':START_ID(CompatibilityRule)']}})\nMATCH (e:Entity {{entity_id: row[':END_ID(Entity)']}})\nMERGE (r)-[:{pred} {{rule_id: row.rule_id}}]->(e);")
 validation="""MATCH (r:CompatibilityRule) RETURN count(r) AS rule_count;\nMATCH (r:CompatibilityRule) WHERE r.status <> 'approved' RETURN r.rule_id;\nMATCH (r:CompatibilityRule) WHERE NOT (r)-[:TARGETS]->(:Entity) RETURN r.rule_id;\nMATCH (r:CompatibilityRule)-[p]->() WHERE type(p) = 'RELATED_TO' RETURN r.rule_id;\n"""
 if not dry:
  (out/"neo4j_constraints.cypher").write_text(constraints,encoding="utf-8");(out/"import_compatibility_rules.cypher").write_text("\n\n".join(imports)+"\n",encoding="utf-8");(out/"validate_import.cypher").write_text(validation,encoding="utf-8")
 files=[p for p in out.iterdir() if p.is_file() and p.name not in ("import_manifest.json","phase11_readiness.json")]
 checks={p.name:sha(p) for p in sorted(files)}
 package={"status":"READY_FOR_CONTROLLED_IMPORT","release_version":manifest["release_version"],"rule_count":len(rules),"predicate_counts":{k:len(v) for k,v in sorted(by_pred.items())},"production_import_allowed":True,"live_database_modified":False,"files":sorted(checks),"checksums":checks,"safety_notice":"Package only. Execute against staging first and obtain operator approval before production import.","generated_at":NOW}
 dump(out/"import_manifest.json",package,dry);dump(out/"phase11_readiness.json",{**readiness,"status":"READY_FOR_CONTROLLED_IMPORT","production_import_allowed":True,"blocking_issues":[]},dry)
 return 0
def main(argv=None):
 p=argparse.ArgumentParser(description="Build Phase 11 Neo4j compatibility import package");p.add_argument("--release-dir",default="CompatibilityLayer/releases/v1.0");p.add_argument("--output-dir",default="neo4j/import/compatibility-v1.0");p.add_argument("--dry-run",action="store_true");a=p.parse_args(argv);return run(ROOT/a.release_dir,ROOT/a.output_dir,a.dry_run)
if __name__=="__main__":sys.exit(main())
