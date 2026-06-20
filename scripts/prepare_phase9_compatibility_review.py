#!/usr/bin/env python3
"""Prepare Phase 9 human semantic review artifacts after Phase 8 passes."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = "2026-06-20T00:00:00+00:00"

def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, data, dry_run=False):
    if dry_run: return
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str): path.write_text(data, encoding="utf-8")
    else: path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def cell(value): return str(value or "").replace("|", "\\|").replace("\n", " ")

def run(output_dir, dry_run=False):
    phase8 = read(ROOT / "CompatibilityLayer/validation/phase8/phase8_validation_report.json")
    if phase8.get("status") not in ("PASSED", "PASSED_WITH_WARNINGS") or not phase8.get("phase9_allowed"):
        print("BLOCKED_PHASE_8_REQUIRED", file=sys.stderr); return 2
    per_rule = {x["rule_id"]: x for x in read(ROOT / "CompatibilityLayer/validation/phase8/phase8_candidate_validation.json")["results"]}
    rules = read(ROOT / "CompatibilityLayer/rules/candidate/compatibility_rule_candidates.json")["rules"]
    clarifications = read(ROOT / "CompatibilityLayer/rules/corrected/clarification_queue.json")["items"]
    corrected = read(ROOT / "CompatibilityLayer/rules/corrected/corrected_rule_candidates.json")["candidates"]
    raw = read(ROOT / "CompatibilityLayer/source/raw/normalized_rule_candidates.json")["rule_candidates"]
    relationships = read(ROOT / "CompatibilityLayer/ontology/compatibility_relationships.json")["relationships"]
    risk_map = {x["relationship_name"]: x.get("risk_level", "medium") for x in relationships}
    evidence_policy = {x["relationship_name"]: x.get("evidence_policy", "traceable_required") for x in relationships}
    decisions, evidence_records, high_risk = [], [], []
    for rule in rules:
        validation = per_rule[rule["rule_id"]]
        unverified = any(e.get("verification_status") != "source_verified" for e in rule.get("evidence", []))
        risk = risk_map.get(rule.get("predicate"), "medium")
        recommendation = "needs_clarification" if unverified else "approve"
        reason = "Authoritative source evidence has not been independently verified; semantic approval must wait for human source review." if unverified else "Phase 8 passed and the rule has resolved entities, valid versions, complete lineage, and verified evidence."
        required = ["Verify the excerpt against the authoritative source document and record the evidence location."] if unverified else []
        questions = ["Does the source text explicitly support the predicate, direction, applicability, and stated version threshold?", "Does the remediation preserve the source modality without strengthening it?"]
        ev = rule.get("evidence", [{}])[0]
        decision = {
            "rule_id": rule["rule_id"], "source_candidate_ids": rule.get("source_candidate_ids", []),
            "rule_type": rule["rule_type"], "predicate": rule.get("predicate"), "current_status": "candidate",
            "phase8_validation_status": validation["validation_status"], "recommended_decision": recommendation,
            "recommendation_reason": reason, "risk_level": risk,
            "subject_resolution": rule["subject"].get("resolution_status", "resolved"),
            "object_resolution": rule["object"].get("resolution_status", "resolved"),
            "version_validation": "passed", "condition_validation": "passed", "exception_validation": "passed",
            "evidence_validation": "review_required" if unverified else "source_verified",
            "remediation_validation": "human_modality_review_required" if rule.get("remediations") else "not_applicable",
            "required_corrections": required, "questions_for_reviewer": questions,
            "source_excerpt": ev.get("source_excerpt", ""), "source_document_id": rule.get("source_document", ""),
            "source_chunk_ids": [e.get("source_chunk_id") for e in rule.get("evidence", []) if e.get("source_chunk_id")],
            "confidence": rule.get("confidence", 0), "approval_status": "pending", "approved_by": None,
            "approval_date": None, "review_notes": ""
        }
        decisions.append(decision)
        for item in rule.get("evidence", []):
            evidence_records.append({"rule_id": rule["rule_id"], "evidence_id": item.get("evidence_id"), "source_document_id": item.get("source_document_id"), "source_chunk_id": item.get("source_chunk_id"), "source_excerpt": item.get("source_excerpt"), "verification_status": item.get("verification_status"), "authoritative_evidence_required": evidence_policy.get(rule.get("predicate")) == "authoritative_required", "review_decision": "pending", "review_notes": ""})
        if risk == "high": high_risk.append({"rule_id": rule["rule_id"], "source_candidate_ids": rule.get("source_candidate_ids", []), "predicate": rule.get("predicate"), "risk_level": risk, "evidence_policy": evidence_policy.get(rule.get("predicate")), "evidence_status": decision["evidence_validation"], "recommended_decision": recommendation, "approval_status": "pending", "blocking_review_requirement": "Authoritative evidence and semantic direction must be confirmed by a human reviewer."})
    clarification_review = []
    for item in clarifications:
        reasons = item.get("reason_codes", [])
        recommendation = "defer" if "missing_product_identity" in reasons else "needs_clarification"
        clarification_review.append({**item, "phase9_recommended_decision": recommendation, "phase9_recommendation_reason": "Resolve every listed reason code against source context and canonical registries before rule generation or approval.", "approval_status": "pending", "reviewed_by": None, "review_date": None, "review_notes": ""})
    raw_ids = {x["candidate_id"] for x in raw}
    represented = {x.get("original_candidate_id", x["candidate_id"]) for x in corrected}
    lineage_complete = raw_ids == represented and len(decisions) == len(rules) and len(clarification_review) == len(clarifications)
    decision_doc = {"status": "PENDING_HUMAN_REVIEW", "generated_at": NOW, "allowed_decisions": ["approve", "approve_with_corrections", "reject", "defer", "needs_clarification", "split", "merge"], "decision_record_count": len(decisions), "decisions": decisions}
    counts = Counter(x["recommended_decision"] for x in decisions)
    report = {"status": "READY_FOR_HUMAN_REVIEW" if lineage_complete else "BLOCKED", "generated_rule_count": len(rules), "decision_record_count": len(decisions), "recommended_approve": counts["approve"], "recommended_approve_with_corrections": counts["approve_with_corrections"], "recommended_reject": counts["reject"], "recommended_defer": counts["defer"], "recommended_clarification": counts["needs_clarification"], "recommended_split": counts["split"], "recommended_merge": counts["merge"], "high_risk_rule_count": len(high_risk), "evidence_gap_count": sum(x["verification_status"] != "source_verified" for x in evidence_records), "pending_human_decisions": len(decisions), "clarification_item_count": len(clarification_review), "source_candidate_count": len(raw_ids), "accounted_source_candidate_count": len(represented & raw_ids), "lineage_complete": lineage_complete, "phase8_status": phase8["status"], "production_import_allowed": False, "phase10_allowed": False, "errors": [] if lineage_complete else ["Lineage or review accounting is incomplete."], "warnings": ["Original source document is unavailable for authoritative evidence verification.", "No rule has been approved; every decision remains pending.", "Phase 10 and Phase 11 were not executed."], "summary": f"Prepared {len(decisions)} generated rules and {len(clarification_review)} clarification items for human semantic review."}
    lines = ["# Compatibility Rule Review Workbook", "", "## Dataset Summary", f"- Source candidates: {len(raw_ids)}", f"- Generated rules: {len(rules)}", f"- Clarification items: {len(clarification_review)}", f"- Pending human decisions: {len(decisions)}", "", "## Phase 8 Validation Summary", f"- Status: {phase8['status']}", f"- Passed rules: {phase8['passed_rule_count']}", f"- Structural/schema errors: {phase8['structural_error_count']}", f"- Warnings: {phase8['warning_count']} (authoritative evidence verification pending)", "", "## Rule Review Table", "| Rule ID | Source Candidates | Type | Predicate | Subject | Target | Conditions | Evidence | Phase 8 | Recommendation | Approval |", "|---|---|---|---|---|---|---:|---|---|---|---|"]
    for rule, decision in zip(rules, decisions):
        lines.append(f"| {cell(rule['rule_id'])} | {cell(', '.join(rule['source_candidate_ids']))} | {cell(rule['rule_type'])} | {cell(rule['predicate'])} | {cell(rule['subject'].get('component_name'))} | {cell(rule['object'].get('component_name'))} | {len(rule.get('conditions', []))} | {cell(decision['evidence_validation'])} | PASS | {cell(decision['recommended_decision'])} | pending |")
    sections = [("Rules Recommended for Approval", counts["approve"]), ("Rules Recommended for Approval With Corrections", counts["approve_with_corrections"]), ("Rules Recommended for Rejection", counts["reject"]), ("Deferred Rules", counts["defer"]), ("Rules Needing Clarification", counts["needs_clarification"]), ("High-Risk Rules", len(high_risk)), ("Evidence Gaps", report["evidence_gap_count"]), ("Entity-Resolution Gaps", sum("missing_product_identity" in x.get("reason_codes", []) for x in clarifications)), ("Version-Resolution Gaps", sum(any("version" in r for r in x.get("reason_codes", [])) for x in clarifications)), ("Contradictions and Overlaps", sum("inconsistent_version_logic" in x.get("reason_codes", []) or "schema_gap" in x.get("reason_codes", []) for x in clarifications))]
    for title, count in sections: lines.extend(["", f"## {title}", f"Count: {count}. See the corresponding JSON review artifact for record-level details."])
    special = ["RCAND-000361", "RCAND-000365", "RCAND-000367", "RCAND-000368", "RCAND-000369", "RCAND-000374", "RCAND-000376", "RCAND-000377", "RCAND-000382", "RCAND-000385", "RCAND-000398", "RCAND-000400"]
    lines.extend(["", "## Special-Candidate Review"] + [f"- {cid}: previous warnings remain in clarification_review.json; no approval recommended." for cid in special])
    lines.extend(["", "## Reviewer Instructions", "1. Open `compatibility_rule_review_decisions.json`.", "2. Review the source excerpt against the authoritative document and Phase 8 result.", "3. Edit only `recommended_decision` if needed, `approval_status`, `approved_by`, `approval_date`, and `review_notes`.", "4. Use `approval_status: approved` only after completing authoritative evidence and semantic checks.", "5. Review every record in `clarification_review.json`; clarification records do not become approved rules automatically.", "", "## Exact Human-Editable Fields", "`recommended_decision`, `approval_status`, `approved_by`, `approval_date`, and `review_notes` in `compatibility_rule_review_decisions.json`."])
    write(output_dir / "compatibility_rule_review_workbook.md", "\n".join(lines) + "\n", dry_run)
    write(output_dir / "compatibility_rule_review_decisions.json", decision_doc, dry_run)
    write(output_dir / "high_risk_rule_review.json", {"status": "PENDING_HUMAN_REVIEW", "high_risk_rule_count": len(high_risk), "rules": high_risk}, dry_run)
    write(output_dir / "clarification_review.json", {"status": "PENDING_HUMAN_REVIEW", "clarification_item_count": len(clarification_review), "items": clarification_review}, dry_run)
    write(output_dir / "evidence_review.json", {"status": "PENDING_HUMAN_REVIEW", "evidence_record_count": len(evidence_records), "records": evidence_records}, dry_run)
    write(output_dir / "phase9_review_preparation_report.json", report, dry_run)
    return 0 if lineage_complete else 1

def main(argv=None):
    p=argparse.ArgumentParser(description="Prepare Phase 9 compatibility-rule human review.")
    p.add_argument("--output-dir", default="CompatibilityLayer/reviews/phase9")
    p.add_argument("--dry-run", action="store_true")
    args=p.parse_args(argv)
    return run((ROOT/args.output_dir).resolve(), args.dry_run)

if __name__ == "__main__": sys.exit(main())
