#!/usr/bin/env python3
"""Phase 8 automated validation for Layer 3 compatibility candidates."""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = "2026-06-20T00:00:00+00:00"
SEMVER = re.compile(r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:\.[0-9]+)?$")
RULE_ID = re.compile(r"^CRULE-[A-Z0-9]+-[0-9]{3,}$")
EVIDENCE_ID = re.compile(r"^EVID-[A-Z0-9]+-[0-9]+$")
DOC_ID = re.compile(r"^DOC-[A-Z0-9]+$")

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path, data, dry_run=False):
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def issue(code, field, message, severity="error"):
    return {"validation_rule_id": code, "severity": severity, "field": field, "message": message}

def validate_rule(rule, registry_ids, schema_fields, templates, predicates):
    errors, warnings = [], []
    rid = rule.get("rule_id", "")
    for name, spec in schema_fields.items():
        if spec.get("required") and name not in rule:
            errors.append(issue("SCHEMA-REQUIRED", name, f"{rid}: missing required field {name}"))
    if not RULE_ID.fullmatch(rid): errors.append(issue("VR-040", "rule_id", f"{rid}: invalid canonical rule ID"))
    rtype = rule.get("rule_type")
    if rtype not in templates: errors.append(issue("VR-025", "rule_type", f"{rid}: unknown rule_type {rtype}"))
    if rule.get("status") != "candidate": errors.append(issue("VR-021", "status", f"{rid}: Phase 8 input must remain candidate"))
    if rule.get("approval_status") != "candidate": errors.append(issue("SAFETY-001", "approval_status", f"{rid}: approval status changed"))
    if rule.get("predicate") not in predicates: errors.append(issue("VR-020", "predicate", f"{rid}: unregistered predicate"))
    if rule.get("predicate") == "RELATED_TO": errors.append(issue("SAFETY-002", "predicate", f"{rid}: RELATED_TO is forbidden"))
    for side, code in (("subject", "VR-001"), ("object", "VR-002")):
        obj = rule.get(side) or {}
        if obj.get("entity_id") not in registry_ids: errors.append(issue(code, f"{side}.entity_id", f"{rid}: unresolved registry entity"))
        for key in ("entity_id", "component_name", "knowledge_category", "version_constraint"):
            if key not in obj: errors.append(issue("SCHEMA-PARTICIPANT", f"{side}.{key}", f"{rid}: missing participant field"))
        vc = obj.get("version_constraint") or {}
        for key in ("operator", "version_normalized", "version_scheme", "requirement_kind"):
            if vc.get(key) in (None, ""): errors.append(issue("SCHEMA-VERSION", f"{side}.version_constraint.{key}", f"{rid}: missing version field"))
        if vc.get("version_scheme") == "semantic" and not SEMVER.fullmatch(str(vc.get("version_normalized", ""))):
            errors.append(issue("VR-008" if side == "subject" else "VR-009", f"{side}.version_constraint.version_normalized", f"{rid}: invalid semantic version"))
    if rule.get("subject", {}).get("entity_id") == rule.get("object", {}).get("entity_id"):
        errors.append(issue("VR-007", "subject/object", f"{rid}: self-referential rule"))
    if rule.get("condition_logic") not in ("AND", "OR"): errors.append(issue("VR-033", "condition_logic", f"{rid}: invalid condition logic"))
    conditions = rule.get("conditions", [])
    if rtype == "incompatible_combination" and len(conditions) < 2: errors.append(issue("VR-038", "conditions", f"{rid}: incompatible pair requires two conditions"))
    for i, cond in enumerate(conditions):
        if cond.get("entity_id") and cond["entity_id"] not in registry_ids: errors.append(issue("VR-003", f"conditions[{i}].entity_id", f"{rid}: unknown condition entity"))
        if not cond.get("component_name"): errors.append(issue("SCHEMA-CONDITION", f"conditions[{i}].component_name", f"{rid}: missing component name"))
        if cond.get("version_scheme") == "semantic" and not SEMVER.fullmatch(str(cond.get("version_normalized", ""))): errors.append(issue("VR-010", f"conditions[{i}].version_normalized", f"{rid}: invalid condition version"))
    conf = rule.get("confidence")
    if not isinstance(conf, (int, float)) or not 0 <= conf <= 1: errors.append(issue("VR-012", "confidence", f"{rid}: confidence out of range"))
    threshold = templates.get(rtype, {}).get("minimum_confidence_threshold", 0)
    if isinstance(conf, (int, float)) and conf < threshold: errors.append(issue("VR-013", "confidence", f"{rid}: confidence below {threshold}"))
    if rule.get("severity") not in templates.get(rtype, {}).get("allowed_severities", []): errors.append(issue("VR-032", "severity", f"{rid}: severity not allowed"))
    evidence = rule.get("evidence", [])
    for i, ev in enumerate(evidence):
        if not EVIDENCE_ID.fullmatch(ev.get("evidence_id", "")): errors.append(issue("VR-014", f"evidence[{i}].evidence_id", f"{rid}: invalid evidence ID"))
        if not DOC_ID.fullmatch(ev.get("source_document_id", "")): errors.append(issue("VR-015", f"evidence[{i}].source_document_id", f"{rid}: invalid document ID"))
        if not ev.get("source_excerpt"): errors.append(issue("VR-017", f"evidence[{i}].source_excerpt", f"{rid}: missing excerpt"))
        if not 0 <= ev.get("confidence_score", -1) <= 1: errors.append(issue("VR-018", f"evidence[{i}].confidence_score", f"{rid}: invalid evidence confidence"))
        if ev.get("verification_status") != "source_verified": warnings.append(issue("EVIDENCE-UNVERIFIED", f"evidence[{i}]", f"{rid}: authoritative source verification pending", "warning"))
    if not DOC_ID.fullmatch(rule.get("source_document", "")): errors.append(issue("VR-039", "source_document", f"{rid}: invalid source document"))
    if evidence and rule.get("source_document") not in {e.get("source_document_id") for e in evidence}: warnings.append(issue("VR-034", "source_document", f"{rid}: evidence document mismatch", "warning"))
    for i, rem in enumerate(rule.get("remediations", [])):
        if rem.get("target_entity_id") not in registry_ids: errors.append(issue("VR-005", f"remediations[{i}].target_entity_id", f"{rid}: unresolved remediation target"))
        if not rem.get("target_version"): errors.append(issue("VR-011", f"remediations[{i}].target_version", f"{rid}: missing remediation version"))
    return errors, warnings

def run(output_dir, dry_run=False):
    rules_doc = read(ROOT / "CompatibilityLayer/rules/candidate/compatibility_rule_candidates.json")
    rules = rules_doc.get("rules", [])
    schema = read(ROOT / "CompatibilityLayer/rule_schema/compatibility_rule_schema.json")
    templates_doc = read(ROOT / "CompatibilityLayer/rule_schema/rule_type_templates.json")
    templates = {x["rule_type"]: x for x in templates_doc["templates"]}
    registry = read(ROOT / "ontology/releases/v1.1-rc2/canonical_entity_registry.json")
    registry_ids = {x["entity_id"] for x in registry["entities"]}
    rel = read(ROOT / "ontology/relationship_ontology/v1.0/relationship_types.json")
    predicates = {x.get("relationship_type") or x.get("predicate") or x.get("type") for x in rel.get("relationship_types", [])}
    predicates.discard(None)
    # Layer 3 intentionally extends the base Relationship Ontology vocabulary.
    predicates.update(schema["fields"]["predicate"].get("allowed_values", []))
    traces = read(ROOT / "CompatibilityLayer/rules/candidate/candidate_generation_trace.json")["traces"]
    trace_ids = {x["rule_id"] for x in traces}
    results, all_errors, all_warnings = [], [], []
    seen = set()
    for rule in rules:
        errors, warnings = validate_rule(rule, registry_ids, schema["fields"], templates, predicates)
        if rule.get("rule_id") in seen: errors.append(issue("VR-030", "rule_id", "Duplicate rule ID"))
        seen.add(rule.get("rule_id"))
        if rule.get("rule_id") not in trace_ids: errors.append(issue("LINEAGE-001", "rule_id", "Missing generation trace"))
        all_errors.extend(errors); all_warnings.extend(warnings)
        results.append({"rule_id": rule.get("rule_id"), "source_candidate_ids": rule.get("source_candidate_ids", []), "validation_status": "PASS" if not errors else "FAIL", "error_count": len(errors), "warning_count": len(warnings), "errors": errors, "warnings": warnings})
    raw = read(ROOT / "CompatibilityLayer/source/raw/normalized_rule_candidates.json")
    corrected = read(ROOT / "CompatibilityLayer/rules/corrected/corrected_rule_candidates.json")
    raw_ids = {x["candidate_id"] for x in raw["rule_candidates"]}
    represented = set()
    for x in corrected["candidates"]:
        represented.add(x.get("original_candidate_id", x["candidate_id"]))
    lineage_errors = [] if represented == raw_ids else [issue("LINEAGE-002", "source_candidates", "Source candidate accounting mismatch")]
    all_errors.extend(lineage_errors)
    status = "PASSED_WITH_WARNINGS" if not all_errors and all_warnings else ("PASSED" if not all_errors else "FAILED")
    schema_report = {"status": "PASS" if not all_errors else "FAIL", "schema_id": schema["schema_id"], "schema_version": schema["schema_version"], "rule_count": len(rules), "passed_rule_count": sum(x["validation_status"] == "PASS" for x in results), "failed_rule_count": sum(x["validation_status"] == "FAIL" for x in results), "error_count": len(all_errors), "errors": all_errors}
    lineage_report = {"status": "PASS" if not lineage_errors else "FAIL", "source_candidate_count": len(raw_ids), "accounted_source_candidate_count": len(represented & raw_ids), "generated_rule_count": len(rules), "generation_trace_count": len(traces), "all_generated_rules_traced": {x["rule_id"] for x in rules} == trace_ids, "errors": lineage_errors}
    evidence_report = {"status": "REVIEW_REQUIRED" if all_warnings else "PASS", "rule_count": len(rules), "evidence_record_count": sum(len(x.get("evidence", [])) for x in rules), "source_verified_count": sum(e.get("verification_status") == "source_verified" for x in rules for e in x.get("evidence", [])), "review_required_count": sum(e.get("verification_status") != "source_verified" for x in rules for e in x.get("evidence", [])), "warnings": [x for x in all_warnings if x["validation_rule_id"] == "EVIDENCE-UNVERIFIED"]}
    report = {"status": status, "phase": 8, "generated_rule_count": len(rules), "validated_rule_count": len(results), "passed_rule_count": sum(x["validation_status"] == "PASS" for x in results), "failed_rule_count": sum(x["validation_status"] == "FAIL" for x in results), "structural_error_count": len(all_errors), "warning_count": len(all_warnings), "lineage_complete": not lineage_errors, "production_import_allowed": False, "phase9_allowed": not all_errors, "artifacts": ["phase8_candidate_validation.json", "phase8_schema_validation.json", "phase8_lineage_validation.json", "phase8_evidence_validation.json"], "errors": all_errors, "warnings": all_warnings, "generated_at": NOW}
    write(output_dir / "phase8_candidate_validation.json", {"status": status, "rule_count": len(results), "results": results}, dry_run)
    write(output_dir / "phase8_schema_validation.json", schema_report, dry_run)
    write(output_dir / "phase8_lineage_validation.json", lineage_report, dry_run)
    write(output_dir / "phase8_evidence_validation.json", evidence_report, dry_run)
    write(output_dir / "phase8_validation_report.json", report, dry_run)
    return 0 if not all_errors else 1

def main(argv=None):
    p = argparse.ArgumentParser(description="Validate Layer 3 compatibility candidates for Phase 8.")
    p.add_argument("--output-dir", default="CompatibilityLayer/validation/phase8")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    return run((ROOT / args.output_dir).resolve(), args.dry_run)

if __name__ == "__main__":
    sys.exit(main())
