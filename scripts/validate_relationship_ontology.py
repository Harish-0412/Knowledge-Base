#!/usr/bin/env python3
"""Validate Relationship Ontology v1.0 and its test-only fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RELEASE = ROOT / "ontology/relationship_ontology/v1.0"
DEFAULT_REGISTRY = ROOT / "ontology/releases/v1.1-rc2/canonical_entity_registry.json"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class RelationshipValidator:
    """Schema, registry, rule, collection, and import-policy validator."""

    def __init__(self, release_dir: Path, registry_path: Path):
        self.release_dir = release_dir
        self.registry_path = registry_path
        self.schema = load_json(release_dir / "relationship_record.schema.json")
        self.types_doc = load_json(release_dir / "relationship_types.json")
        self.rules_doc = load_json(release_dir / "relationship_rules.json")
        self.registry = load_json(registry_path)
        self.schema_validator = Draft202012Validator(self.schema)
        self.types = {
            item["relationship_type"]: item
            for item in self.types_doc["relationship_types"]
        }
        self.rules = {
            item["relationship_type"]: item
            for item in self.rules_doc["relationship_rules"]
        }
        self.entities = {
            item["entity_id"]: item for item in self.registry["entities"]
        }
        self.virtual_inverses = {
            item["virtual_inverse_label"]
            for item in self.types.values()
            if item.get("virtual_inverse_label")
        }

    @staticmethod
    def _schema_code(error: Any) -> str:
        path = list(error.absolute_path)
        if error.validator in {"minimum", "maximum"} and path[-1:] == ["confidence"]:
            return "CONFIDENCE_OUT_OF_RANGE"
        if path[-1:] == ["operator"] and error.validator == "enum":
            return "INVALID_CONDITION_OPERATOR"
        if path[-1:] == ["source_type"] and error.validator == "enum":
            return "INVALID_EVIDENCE_SOURCE"
        if error.validator == "additionalProperties":
            return "SCHEMA_ADDITIONAL_PROPERTY"
        if error.validator == "pattern":
            return "SCHEMA_INVALID_PATTERN"
        if error.validator == "enum":
            return "SCHEMA_INVALID_ENUM"
        if error.validator == "required":
            missing = re.search(r"'([^']+)' is a required property", error.message)
            field = missing.group(1) if missing else ""
            if field == "approved_by":
                return "SCHEMA_APPROVER_REQUIRED"
            if field == "approved_at":
                return "SCHEMA_APPROVAL_DATE_REQUIRED"
            if field == "conditions":
                return "SCHEMA_CONDITIONS_REQUIRED"
            return "SCHEMA_REQUIRED_FIELD_MISSING"
        return "SCHEMA_INVALID_VALUE"

    def validate_record_schema(self, record: dict[str, Any]) -> set[str]:
        codes = {self._schema_code(error) for error in self.schema_validator.iter_errors(record)}
        if record.get("assertion_scope") in {"conditional", "version_specific"} and not record.get("conditions"):
            codes.add("SCHEMA_CONDITIONS_REQUIRED")
        if record.get("approval_status") == "approved":
            if not record.get("approved_by"):
                codes.add("SCHEMA_APPROVER_REQUIRED")
            if not record.get("approved_at"):
                codes.add("SCHEMA_APPROVAL_DATE_REQUIRED")
            if record.get("verification_status") not in {"human_approved", "source_verified"}:
                codes.add("SCHEMA_APPROVAL_VERIFICATION_INVALID")
        return codes

    def validate_collection(
        self, records: Iterable[dict[str, Any]], *, production: bool = False
    ) -> list[dict[str, Any]]:
        records = list(records)
        errors: list[dict[str, Any]] = []

        def add(code: str, index: int | None = None) -> None:
            item = {"code": code}
            if index is not None:
                item["record_index"] = index
                item["relationship_id"] = records[index].get("relationship_id")
            if item not in errors:
                errors.append(item)

        for index, record in enumerate(records):
            for code in sorted(self.validate_record_schema(record)):
                add(code, index)

            source_id = record.get("source_id")
            target_id = record.get("target_id")
            predicate = record.get("relationship_type")
            source = self.entities.get(source_id)
            target = self.entities.get(target_id)

            if source_id and not source:
                add("SOURCE_ENTITY_NOT_FOUND", index)
            if target_id and not target:
                add("TARGET_ENTITY_NOT_FOUND", index)
            if source_id and source_id == target_id:
                add("SELF_RELATIONSHIP", index)
            if predicate not in self.types:
                add("UNKNOWN_RELATIONSHIP_TYPE", index)
                if predicate in self.virtual_inverses:
                    add("VIRTUAL_INVERSE_MATERIALIZATION_FORBIDDEN", index)
                continue

            rule = self.rules[predicate]
            type_def = self.types[predicate]
            if source:
                category = source.get("knowledge_category")
                if category not in rule["source_domain"]["allowed_categories"]:
                    add("INVALID_SOURCE_CATEGORY", index)
            if target:
                category = target.get("knowledge_category")
                if category not in rule["target_range"]["allowed_categories"]:
                    add("INVALID_TARGET_CATEGORY", index)
            if source and target:
                same = source.get("knowledge_category") == target.get("knowledge_category")
                if same and rule.get("same_category_policy") == "forbidden":
                    add("FORBIDDEN_SAME_CATEGORY", index)
                if not same and rule.get("cross_category_policy") == "forbidden":
                    add("FORBIDDEN_CROSS_CATEGORY", index)

            evidence = record.get("evidence") or []
            evidence_policy = rule.get("evidence_policy", type_def.get("evidence_policy"))
            if evidence_policy in {"required", "authoritative_required"} and not evidence:
                add("MISSING_REQUIRED_EVIDENCE", index)
            if evidence_policy == "authoritative_required":
                authoritative = {"industry_standard", "official_documentation", "vendor_documentation"}
                if not any(item.get("source_type") in authoritative for item in evidence):
                    add("MISSING_REQUIRED_EVIDENCE", index)

            condition_policy = rule.get("condition_policy", type_def.get("condition_policy"))
            if condition_policy == "required" and not record.get("conditions"):
                add("MISSING_REQUIRED_CONDITIONS", index)
            if record.get("assertion_scope") in {"conditional", "version_specific"} and not record.get("conditions"):
                add("MISSING_REQUIRED_CONDITIONS", index)

            confidence = record.get("confidence")
            if isinstance(confidence, (int, float)) and 0 <= confidence <= 1:
                if confidence < float(rule.get("minimum_confidence", 0)):
                    add("CONFIDENCE_BELOW_MINIMUM", index)

            if production and record.get("approval_status") != "approved":
                add("PRODUCTION_APPROVAL_REQUIRED", index)

        ids: dict[str, list[int]] = defaultdict(list)
        identities: dict[str, list[int]] = defaultdict(list)
        by_predicate_edge: dict[str, set[tuple[str, str]]] = defaultdict(set)
        by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)
        for index, record in enumerate(records):
            if record.get("relationship_id"):
                ids[record["relationship_id"]].append(index)
            identity = canonical({
                "source_id": record.get("source_id"),
                "relationship_type": record.get("relationship_type"),
                "target_id": record.get("target_id"),
                "assertion_scope": record.get("assertion_scope"),
                "conditions": record.get("conditions", []),
            })
            identities[identity].append(index)
            predicate = record.get("relationship_type")
            source_id = record.get("source_id")
            target_id = record.get("target_id")
            if predicate and source_id and target_id:
                by_predicate_edge[predicate].add((source_id, target_id))
                by_pair[(source_id, target_id)].add(predicate)

        for indexes in ids.values():
            if len(indexes) > 1:
                add("RELATIONSHIP_ID_DUPLICATE", indexes[1])
        for indexes in identities.values():
            if len(indexes) > 1:
                add("EXACT_DUPLICATE_RELATIONSHIP", indexes[1])

        for predicate, edges in by_predicate_edge.items():
            rule = self.rules.get(predicate, {})
            for source_id, target_id in edges:
                if (target_id, source_id) not in edges:
                    continue
                if rule.get("cycle_policy") == "forbidden":
                    add("FORBIDDEN_CYCLE")
                elif rule.get("cycle_policy") in {"review", "review_required"}:
                    add("REVIEW_REQUIRED_CYCLE")
                else:
                    add("RECIPROCAL_NON_SYMMETRIC_RELATIONSHIP")

        contradiction_sets = [
            {"COMPATIBLE_WITH", "CONFLICTS_WITH"},
            {"SUPPORTS", "CONFLICTS_WITH"},
            {"REQUIRES", "CONFLICTS_WITH"},
            {"IS_A", "PART_OF"},
        ]
        for predicates in by_pair.values():
            if any(required <= predicates for required in contradiction_sets):
                add("CONTRADICTORY_RELATIONSHIPS")

        return errors


def ontology_report(validator: RelationshipValidator) -> dict[str, Any]:
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    try:
        Draft202012Validator.check_schema(validator.schema)
        checks.append({"check": "draft_2020_12_schema", "status": "PASS"})
    except Exception as exc:  # jsonschema supplies the diagnostic
        errors.append(f"Invalid relationship schema: {exc}")

    names = list(validator.types)
    checks.append({"check": "registered_relationship_types", "actual": len(names), "expected": 20,
                   "status": "PASS" if len(names) == 20 else "FAIL"})
    if len(names) != 20:
        errors.append("Relationship type count must be exactly 20.")
    if len(names) != len(set(names)):
        errors.append("Relationship type names are not unique.")
    if "RELATED_TO" in names:
        errors.append("RELATED_TO is excluded from the semantic vocabulary.")

    rule_names = list(validator.rules)
    aligned = len(rule_names) == 20 and set(rule_names) == set(names)
    checks.append({"check": "type_rule_alignment", "status": "PASS" if aligned else "FAIL"})
    if not aligned:
        errors.append("Relationship rules must align one-to-one with registered types.")

    examples = validator.schema.get("examples", [])
    example_errors = sum((len(validator.validate_record_schema(item)) for item in examples), 0)
    checks.append({"check": "schema_examples", "count": len(examples), "errors": example_errors,
                   "status": "PASS" if not example_errors else "FAIL"})
    if example_errors:
        errors.append("One or more embedded schema examples are invalid.")

    return {
        "mode": "ontology",
        "status": "PASS" if not errors else "FAIL",
        "relationship_ontology_version": validator.types_doc["relationship_ontology_version"],
        "entity_registry_version": validator.registry["registry_version"],
        "registered_relationship_type_count": len(names),
        "relationship_rule_count": len(rule_names),
        "checks": checks,
        "errors": errors,
        "warnings": [],
        "summary": "Relationship ontology self-test passed." if not errors else "Relationship ontology self-test failed.",
    }


def fixture_report(validator: RelationshipValidator) -> dict[str, Any]:
    valid_doc = load_json(validator.release_dir / "examples/valid_relationships.json")
    invalid_doc = load_json(validator.release_dir / "examples/invalid_relationships.json")
    valid_failures = []
    for record in valid_doc["relationships"]:
        errors = validator.validate_collection([record])
        if errors:
            valid_failures.append({"relationship_id": record.get("relationship_id"), "errors": errors})

    invalid_results = []
    for case in invalid_doc["cases"]:
        production = case.get("validation_layer") == "approval"
        errors = validator.validate_collection(case["records"], production=production)
        actual = sorted({item["code"] for item in errors})
        expected = sorted(case["expected_error_codes"])
        missing = sorted(set(expected) - set(actual))
        invalid_results.append({
            "case_id": case["case_id"],
            "expected_error_codes": expected,
            "actual_error_codes": actual,
            "missing_expected_error_codes": missing,
            "status": "PASS" if not missing else "FAIL",
        })

    failed_invalid = [item for item in invalid_results if item["status"] == "FAIL"]
    status = "PASS" if not valid_failures and not failed_invalid else "FAIL"
    return {
        "mode": "fixtures",
        "status": status,
        "relationship_ontology_version": validator.types_doc["relationship_ontology_version"],
        "entity_registry_version": validator.registry["registry_version"],
        "valid_relationships": {
            "executed": len(valid_doc["relationships"]),
            "passed": len(valid_doc["relationships"]) - len(valid_failures),
            "failed": len(valid_failures),
            "failures": valid_failures,
        },
        "invalid_cases": {
            "executed": len(invalid_results),
            "passed": len(invalid_results) - len(failed_invalid),
            "failed": len(failed_invalid),
            "results": invalid_results,
        },
        "production_import_allowed": False,
        "errors": [],
        "warnings": [],
        "summary": "All relationship fixtures produced their required validation results." if status == "PASS" else "Relationship fixture execution failed.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("ontology", "fixtures"))
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validator = RelationshipValidator(args.release_dir, args.registry)
        report = ontology_report(validator) if args.mode == "ontology" else fixture_report(validator)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"Configuration or file-loading error: {exc}", file=sys.stderr)
        return 3
    if args.output:
        write_json(args.output, report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
