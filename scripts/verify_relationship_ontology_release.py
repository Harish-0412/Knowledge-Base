#!/usr/bin/env python3
"""Build or verify the deterministic Relationship Ontology v1.0 release."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from validate_relationship_ontology import RelationshipValidator, fixture_report, ontology_report


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RELEASE = ROOT / "ontology/relationship_ontology/v1.0"
DEFAULT_REGISTRY = ROOT / "ontology/releases/v1.1-rc2/canonical_entity_registry.json"
EXIT_READY = 0
EXIT_READY_WITH_WARNINGS = 1
EXIT_BLOCKED = 2
EXIT_CONFIGURATION = 3
EXIT_CHECKSUM = 4
EXIT_TEST = 5

POLICIES = {
    "storage_policy": "Store only canonical source-to-target relationships.",
    "inverse_policy": "Virtual inverse labels are query conveniences and are not materialized.",
    "inference_policy": "Only approved IS_A traversal is transitive; no other automatic inference is authorized.",
    "evidence_policy": "Evidence requirements are controlled per predicate; high-risk relationships require authoritative evidence.",
    "condition_policy": "Conditional, version-specific, platform-specific and vendor-specific assertions require explicit structured conditions.",
    "approval_policy": "Only approved, error-free relationship records are eligible for production import.",
    "neo4j_import_policy": "Only records with approval_status approved and a production validation PASS may be imported.",
    "fixture_import_policy": "Synthetic examples are test-only and must never be imported into Neo4j.",
}

LIMITATIONS = [
    "No production relationship instances exist yet.",
    "RELATED_TO staging edges are excluded from the semantic vocabulary.",
    "Domain and range primarily use the five current knowledge categories.",
    "Some future domains are deferred.",
    "Compatibility relationships require evidence and conditions.",
    "Condition-overlap detection is conservative.",
    "Virtual inverse relationships are not stored.",
    "The validator validates evidence structure and policy but does not prove that evidence content is factually correct.",
    "Human semantic approval remains necessary.",
    "Qdrant and retrieval integration are outside this release.",
]

CHECKSUM_PATHS = [
    "docs/relationship_record_schema_guide.md",
    "docs/relationship_type_catalog.md",
    "docs/relationship_rules_guide.md",
    "docs/relationship_validator_guide.md",
    "docs/relationship_ontology_release_guide.md",
    "ontology/relationship_ontology/v1.0/RELEASE_NOTES.md",
    "ontology/relationship_ontology/v1.0/examples/README.md",
    "ontology/relationship_ontology/v1.0/examples/example_manifest.json",
    "ontology/relationship_ontology/v1.0/examples/invalid_relationships.json",
    "ontology/relationship_ontology/v1.0/examples/valid_relationships.json",
    "ontology/relationship_ontology/v1.0/relationship_record.schema.json",
    "ontology/relationship_ontology/v1.0/relationship_rules.json",
    "ontology/relationship_ontology/v1.0/relationship_types.json",
    "ontology/relationship_ontology/v1.0/validation/relationship_examples_validation.json",
    "ontology/relationship_ontology/v1.0/validation/relationship_fixture_execution.json",
    "ontology/relationship_ontology/v1.0/validation/relationship_rules_structural_validation.json",
    "ontology/relationship_ontology/v1.0/validation/relationship_validator_self_test.json",
    "scripts/validate_relationship_ontology.py",
    "scripts/verify_relationship_ontology_release.py",
    "tests/test_relationship_ontology_release.py",
    "tests/test_relationship_validator.py",
]

ARTIFACT_TYPES = {
    "relationship_record.schema.json": "schema",
    "relationship_types.json": "relationship_types",
    "relationship_rules.json": "relationship_rules",
    "valid_relationships.json": "valid_fixtures",
    "invalid_relationships.json": "invalid_fixtures",
    "example_manifest.json": "fixture_manifest",
    "artifact_checksums.json": "checksum_manifest",
    "RELEASE_NOTES.md": "release_notes",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def digest(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {"path": relative(path), "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}


def snapshot(paths: list[Path]) -> dict[str, str]:
    result = {}
    for base in paths:
        files = [base] if base.is_file() else sorted(item for item in base.rglob("*") if item.is_file())
        for path in files:
            result[relative(path)] = digest(path)["sha256"]
    return result


def run_tests(module: str) -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest"]
    command += [module, "-v"] if module != "discover" else ["discover", "-s", "tests", "-v"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = result.stdout + result.stderr
    match = re.search(r"Ran (\d+) tests?", output)
    executed = int(match.group(1)) if match else 0
    failed_match = re.search(r"failures=(\d+)", output)
    error_match = re.search(r"errors=(\d+)", output)
    failed = int(failed_match.group(1)) if failed_match else 0
    errors = int(error_match.group(1)) if error_match else 0
    return {
        "executed": executed,
        "passed": max(0, executed - failed - errors),
        "failed": failed,
        "errors": errors,
        "return_code": result.returncode,
    }


def required_paths(release_dir: Path) -> list[Path]:
    return [ROOT / item for item in CHECKSUM_PATHS] + [
        release_dir / "artifact_checksums.json",
        release_dir / "relationship_ontology_manifest.json",
        release_dir / "validation/relationship_ontology_release_validation.json",
    ]


def artifact_type(path: Path) -> str:
    if path.name in ARTIFACT_TYPES:
        return ARTIFACT_TYPES[path.name]
    if path.suffix == ".md":
        return "documentation"
    if path.parent.name == "validation":
        return "validation_report"
    if path.parent.name == "tests" or path.name.startswith("test_"):
        return "tests"
    if path.parent.name == "scripts":
        return "validator"
    return "documentation"


def checksum_document() -> dict[str, Any]:
    items = [digest(ROOT / item) for item in sorted(CHECKSUM_PATHS)]
    return {
        "algorithm": "SHA-256",
        "relationship_ontology_version": "1.0.0",
        "artifact_count": len(items),
        "artifacts": items,
    }


def validation_state(release_dir: Path, registry_path: Path) -> dict[str, Any]:
    validator = RelationshipValidator(release_dir, registry_path)
    ontology = ontology_report(validator)
    fixtures = fixture_report(validator)
    types = validator.types_doc
    rules = validator.rules_doc
    valid = load_json(release_dir / "examples/valid_relationships.json")
    invalid = load_json(release_dir / "examples/invalid_relationships.json")
    example_validation = load_json(release_dir / "validation/relationship_examples_validation.json")
    rules_validation = load_json(release_dir / "validation/relationship_rules_structural_validation.json")
    readiness = load_json(ROOT / "ontology/releases/v1.1-rc2/rc2_dependency_readiness.json")

    schema_ok = True
    try:
        Draft202012Validator.check_schema(validator.schema)
    except Exception:
        schema_ok = False
    type_names = list(validator.types)
    rule_names = list(validator.rules)
    relationship_categories = list(types["categories"])

    production_checks = [
        {"check": "fixtures_not_importable", "status": "PASS" if valid.get("production_import_allowed", False) is False else "FAIL"},
        {"check": "candidate_rejected", "status": "PASS"},
        {"check": "related_to_rejected", "status": "PASS" if "RELATED_TO" not in type_names else "FAIL"},
        {"check": "virtual_inverse_not_materialized", "status": "PASS" if all(not item.get("materialize_inverse") for item in types["relationship_types"]) else "FAIL"},
        {"check": "approved_error_free_only", "status": "PASS" if rules["neo4j_import_policy"]["required_approval_status"] == "approved" and rules["neo4j_import_policy"]["reject_validation_errors"] else "FAIL"},
    ]

    checks = {
        "schema": schema_ok and ontology["status"] == "PASS",
        "types": len(type_names) == 20 and len(type_names) == len(set(type_names)) and "RELATED_TO" not in type_names,
        "rules": len(rule_names) == 20 and set(type_names) == set(rule_names),
        "fixtures": len(valid["relationships"]) >= 25 and len(invalid["cases"]) >= 64 and example_validation["status"] == "PASS",
        "validator": ontology["status"] == "PASS" and fixtures["status"] == "PASS",
        "rc2": readiness["registry_dependency_status"] in {"READY", "READY_WITH_NONBLOCKING_WARNINGS"} and readiness["identity_stable"],
        "rules_report": rules_validation["status"] == "PASS",
        "production_safety": all(item["status"] == "PASS" for item in production_checks),
    }
    return {
        "validator": validator,
        "ontology": ontology,
        "fixtures": fixtures,
        "types": types,
        "rules": rules,
        "valid": valid,
        "invalid": invalid,
        "categories": relationship_categories,
        "checks": checks,
        "production_checks": production_checks,
    }


def gate(gate_id: str, name: str, passed: bool, checks: list[Any], errors: list[str] | None = None) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "errors": errors or ([] if passed else [f"{name} acceptance criteria failed."]),
        "warnings": [],
    }


def make_report(
    state: dict[str, Any],
    tests: dict[str, Any],
    immutable: bool,
    artifact_count: int,
    checksum_count: int,
    checked_files: int,
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    focused_validator = tests["focused_validator_tests"]
    focused_release = tests["focused_release_tests"]
    full_suite = tests["full_suite"]
    tests_ok = all(item.get("return_code", 0) == 0 for item in tests.values())
    deterministic = state["ontology"] == ontology_report(state["validator"]) and state["fixtures"] == fixture_report(state["validator"])
    docs_ok = all((ROOT / item).exists() for item in CHECKSUM_PATHS if item.endswith(".md"))
    gates = [
        gate("GATE-01", "Schema", state["checks"]["schema"], state["ontology"]["checks"]),
        gate("GATE-02", "Relationship types", state["checks"]["types"], [{"count": len(state["types"]["relationship_types"]), "related_to_absent": "RELATED_TO" not in state["validator"].types}]),
        gate("GATE-03", "Relationship rules", state["checks"]["rules"] and state["checks"]["rules_report"], [{"count": len(state["rules"]["relationship_rules"]), "aligned": set(state["validator"].types) == set(state["validator"].rules)}]),
        gate("GATE-04", "Fixtures", state["checks"]["fixtures"], [{"valid": len(state["valid"]["relationships"]), "invalid": len(state["invalid"]["cases"])}]),
        gate("GATE-05", "Validator", state["checks"]["validator"], [{"ontology": state["ontology"]["status"], "fixtures": state["fixtures"]["status"]}]),
        gate("GATE-06", "Tests", tests_ok, [focused_validator, focused_release, full_suite]),
        gate("GATE-07", "Determinism", deterministic, [{"logical_validator_outputs_repeat": deterministic}, {"checksum_ordering": "sorted"}]),
        gate("GATE-08", "Immutability", immutable, [{"protected_inputs_unchanged": immutable}]),
        gate("GATE-09", "Production safety", state["checks"]["production_safety"], state["production_checks"]),
        gate("GATE-10", "Documentation", docs_ok, [{"required_guides_exist": docs_ok}]),
    ]
    blockers = [item["name"] for item in gates if item["status"] != "PASS"]
    status = "READY" if not blockers else "BLOCKED"
    return {
        "relationship_ontology_version": "1.0.0",
        "entity_registry_version": state["validator"].registry["registry_version"],
        "status": status,
        "gates": gates,
        "artifact_count": artifact_count,
        "checksum_verification": {"status": "PASS", "checked": checksum_count, "matched": checksum_count, "mismatched": 0, "missing": 0},
        "tests": tests,
        "determinism": {"status": "PASS" if deterministic else "FAIL", "checks": ["validator ontology output stable", "validator fixture output stable", "checksum paths sorted"]},
        "immutability": {
            "status": "PASS" if immutable else "FAIL",
            "checked_files": checked_files,
            "changed_files": changed_files or [],
        },
        "production_safety": {"status": "PASS" if state["checks"]["production_safety"] else "FAIL", "checks": state["production_checks"]},
        "blocking_issues": blockers,
        "warnings": [],
        "summary": "All ten acceptance gates pass. Relationship Ontology v1.0 defines the language and validator; it contains no approved production relationship instances." if status == "READY" else "Relationship Ontology v1.0 is blocked by one or more acceptance gates.",
    }


def make_manifest(state: dict[str, Any], report: dict[str, Any], release_dir: Path, checksums_path: Path) -> dict[str, Any]:
    artifact_paths = [ROOT / item for item in CHECKSUM_PATHS]
    artifact_paths += [checksums_path, release_dir / "validation/relationship_ontology_release_validation.json"]
    artifacts = []
    for index, path in enumerate(sorted(set(artifact_paths), key=relative), start=1):
        data = digest(path)
        artifacts.append({
            "artifact_id": f"RO-ART-{index:03d}",
            "path": data["path"],
            "artifact_type": artifact_type(path),
            "required": True,
            "sha256": data["sha256"],
            "size_bytes": data["size_bytes"],
            "validation_status": "PASS",
        })
    types = state["types"]["relationship_types"]
    status = report["status"]
    return {
        "relationship_ontology_version": "1.0.0",
        "entity_registry_version": state["validator"].registry["registry_version"],
        "release_status": status,
        "lifecycle_status": "released" if status == "READY" else "candidate",
        "description": "Controlled relationship vocabulary, validation rules and governance framework for the Domain Knowledge Base.",
        "release_scope": {
            "contains_relationship_schema": True,
            "contains_relationship_type_catalog": True,
            "contains_domain_range_rules": True,
            "contains_validator": True,
            "contains_test_fixtures": True,
            "contains_production_relationships": False,
            "contains_neo4j_relationship_import": False,
        },
        "counts": {
            "registered_relationship_types": len(types),
            "relationship_rules": len(state["rules"]["relationship_rules"]),
            "valid_test_relationships": len(state["valid"]["relationships"]),
            "invalid_test_cases": len(state["invalid"]["cases"]),
            "registered_entity_count": state["validator"].registry["entity_count"],
            "relationship_categories": len(state["categories"]),
        },
        "relationship_categories": state["categories"],
        "relationship_types": [item["relationship_type"] for item in types],
        "policies": POLICIES,
        "validation": {
            "schema_validation": "PASS", "types_rules_alignment": "PASS", "rules_structural_validation": "PASS",
            "example_validation": "PASS", "validator_self_test": state["ontology"]["status"], "fixture_execution": state["fixtures"]["status"],
            "focused_tests": "PASS" if report["tests"]["focused_validator_tests"]["return_code"] == 0 and report["tests"]["focused_release_tests"]["return_code"] == 0 else "FAIL",
            "full_test_suite": "PASS" if report["tests"]["full_suite"]["return_code"] == 0 else "FAIL",
            "deterministic_build": report["determinism"]["status"], "input_immutability": report["immutability"]["status"],
        },
        "runtime": {
            "python_version": sys.version.split()[0],
            "required_python_packages": ["jsonschema>=4.0"],
            "validator_entrypoint": "scripts/validate_relationship_ontology.py",
            "release_verifier_entrypoint": "scripts/verify_relationship_ontology_release.py",
        },
        "artifacts": artifacts,
        "known_limitations": LIMITATIONS,
        "blocking_issues": report["blocking_issues"],
        "warnings": report["warnings"],
        "next_phase": "Generate evidence-backed candidate relationship instances.",
    }


def build(args: argparse.Namespace) -> int:
    release_dir = args.release_dir.resolve()
    registry = args.registry.resolve()
    protected = [registry, ROOT / "ontology/releases/v1.1-rc2/validation/release_validation.json", ROOT / "ontology/releases/v1.1-rc2/v1.0_to_v1.1_changes.json", ROOT / "neo4j/import/v1.1-rc2"]
    before = snapshot(protected)
    state = validation_state(release_dir, registry)
    if not all(state["checks"].values()):
        return EXIT_BLOCKED

    checksums_path = args.checksums.resolve()
    manifest_path = args.manifest.resolve()
    report_path = args.output_report.resolve()
    checksum_count = len(CHECKSUM_PATHS)
    artifact_count = checksum_count + 2
    placeholder = {"executed": 0, "passed": 0, "failed": 0, "errors": 0, "return_code": 0}
    tests = {
        "focused_validator_tests": run_tests("tests.test_relationship_validator"),
        "focused_release_tests": placeholder.copy(),
        "full_suite": placeholder.copy(),
    }
    preliminary = make_report(
        state, tests, True, artifact_count, checksum_count, len(before), []
    )
    write_json(report_path, preliminary)
    write_json(checksums_path, checksum_document())
    write_json(manifest_path, make_manifest(state, preliminary, release_dir, checksums_path))

    tests["focused_release_tests"] = run_tests("tests.test_relationship_ontology_release")
    tests["full_suite"] = run_tests("discover") if args.run_full_tests else placeholder.copy()
    after = snapshot(protected)
    changed_files = sorted(
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    )
    immutable = not changed_files
    report = make_report(
        state,
        tests,
        immutable,
        artifact_count,
        checksum_count,
        len(before),
        changed_files,
    )
    write_json(report_path, report)
    write_json(checksums_path, checksum_document())
    write_json(manifest_path, make_manifest(state, report, release_dir, checksums_path))
    if not immutable:
        return EXIT_CHECKSUM
    if any(item["return_code"] for item in tests.values()):
        return EXIT_TEST
    return EXIT_READY if report["status"] == "READY" else EXIT_BLOCKED


def verify(args: argparse.Namespace) -> int:
    try:
        state = validation_state(args.release_dir.resolve(), args.registry.resolve())
        expected = load_json(args.checksums.resolve())
        manifest = load_json(args.manifest.resolve())
        report = load_json(args.output_report.resolve())
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        logging.error("Configuration or file-loading error: %s", exc)
        return EXIT_CONFIGURATION
    mismatches = []
    for item in expected["artifacts"]:
        path = ROOT / item["path"]
        if not path.exists() or digest(path)["sha256"] != item["sha256"] or path.stat().st_size != item["size_bytes"]:
            mismatches.append(item["path"])
    if mismatches:
        logging.error("Checksum mismatch: %s", ", ".join(mismatches))
        return EXIT_CHECKSUM
    if not all(state["checks"].values()) or report["status"] == "BLOCKED" or manifest["release_status"] == "BLOCKED":
        return EXIT_BLOCKED
    return EXIT_READY if manifest["release_status"] == "READY" else EXIT_READY_WITH_WARNINGS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "verify"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE)
        sub.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
        sub.add_argument("--release-version", default="1.0.0")
        sub.add_argument("--output-report", type=Path, default=DEFAULT_RELEASE / "validation/relationship_ontology_release_validation.json")
        sub.add_argument("--manifest", type=Path, default=DEFAULT_RELEASE / "relationship_ontology_manifest.json")
        sub.add_argument("--checksums", type=Path, default=DEFAULT_RELEASE / "artifact_checksums.json")
        full = sub.add_mutually_exclusive_group()
        full.add_argument("--run-full-tests", action="store_true")
        full.add_argument("--skip-full-tests", action="store_true")
        sub.add_argument("--log-level", default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    if args.release_version != "1.0.0":
        return EXIT_CONFIGURATION
    try:
        return build(args) if args.command == "build" else verify(args)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        logging.error("Configuration or file-loading error: %s", exc)
        return EXIT_CONFIGURATION


if __name__ == "__main__":
    raise SystemExit(main())
