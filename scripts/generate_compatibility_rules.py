#!/usr/bin/env python3
"""
Phase 7: Generate structured Layer 3 candidate compatibility rules.

CLI:
    python scripts/generate_compatibility_rules.py \\
        --corrected-input CompatibilityLayer/rules/corrected/corrected_rule_candidates.json \\
        --compatibility-ontology CompatibilityLayer/ontology \\
        --domain-registry ontology/releases/v1.1-rc2/canonical_entity_registry.json \\
        --output-dir CompatibilityLayer/rules/candidate \\
        --clarification-dir CompatibilityLayer/rules/needs_clarification \\
        [--product-registry <optional path>] \\
        [--dry-run] [--log-level DEBUG|INFO|WARNING]
"""
import argparse
import hashlib
import json
import logging
import pathlib
import subprocess
import sys
from typing import List, Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent

REGISTERED_PREDICATES = {
    "REQUIRES", "SUPPORTS", "CONFLICTS_WITH", "FIXED_BY", "UPGRADE_TO",
    "DEPENDS_ON", "REMEDIATES", "BLOCKS", "SUPERSEDES", "REFERENCES",
    "HAS_CONDITION", "HAS_EXCEPTION", "HAS_EVIDENCE", "HAS_REMEDIATION",
    "VALIDATED_BY", "APPROVED_BY", "DERIVED_FROM", "REPLACES",
    "TARGETS", "SUPPORTED_BY",
}

FORBIDDEN_PREDICATES = {"RELATED_TO"}


def validate_generated_rules(rules: list, logger: logging.Logger) -> bool:
    """Validate key invariants on generated rules. Returns True if all pass."""
    ok = True
    seen_ids = set()
    for rule in rules:
        rid = rule.get("rule_id", "")
        # Unique IDs
        if rid in seen_ids:
            logger.error(f"DUPLICATE rule_id: {rid}")
            ok = False
        seen_ids.add(rid)
        # Approval status must be candidate
        if rule.get("approval_status") != "candidate":
            logger.error(f"{rid}: approval_status must be 'candidate'")
            ok = False
        # No approved status
        if rule.get("verification_status") == "source_verified":
            logger.error(f"{rid}: verification_status must not be source_verified")
            ok = False
        # Predicate must be registered
        pred = rule.get("predicate")
        if pred and pred not in REGISTERED_PREDICATES:
            logger.error(f"{rid}: predicate '{pred}' not registered")
            ok = False
        if pred in FORBIDDEN_PREDICATES:
            logger.error(f"{rid}: forbidden predicate '{pred}'")
            ok = False
        # No literal 'unknown' entities
        for side in ("subject", "object"):
            ename = (rule.get(side) or {}).get("entity_name", "")
            if str(ename).lower() == "unknown":
                logger.error(f"{rid}: {side}.entity_name is literal 'unknown'")
                ok = False
        # Production import must be false
        if rule.get("production_import_allowed", False):
            logger.error(f"{rid}: production_import_allowed must be False")
            ok = False
    return ok


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 7: Generate structured compatibility rule candidates.")
    parser.add_argument("--corrected-input", required=True,
                        help="Path to corrected_rule_candidates.json")
    parser.add_argument("--compatibility-ontology", required=True,
                        help="Directory containing compatibility ontology files")
    parser.add_argument("--domain-registry", required=True,
                        help="Path to RC2 canonical_entity_registry.json")
    parser.add_argument("--product-registry", default=None,
                        help="Optional path to Layer 2 product registry")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory for generated candidate rules")
    parser.add_argument("--clarification-dir", required=True,
                        help="Output directory for clarification-required rules")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run generation logic without writing files")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level),
                        format="%(levelname)s %(message)s")
    logger = logging.getLogger("generate_rules")

    corrected_path = ROOT / args.corrected_input
    if not corrected_path.exists():
        logger.error(f"Corrected input not found: {corrected_path}")
        logger.error("Run 'python build_phase6_7.py' first to generate corrected candidates.")
        return 1

    domain_path = ROOT / args.domain_registry
    if not domain_path.exists():
        logger.error(f"Domain registry not found: {domain_path}")
        return 1

    corrected_data = json.loads(corrected_path.read_text(encoding="utf-8"))
    candidates = corrected_data.get("candidates", [])
    logger.info(f"Loaded {len(candidates)} corrected candidates")

    # Validate registry
    registry = json.loads(domain_path.read_text(encoding="utf-8"))
    rc2_ids = {e["entity_id"] for e in registry.get("entities", [])}
    logger.info(f"RC2 registry loaded: {len(rc2_ids)} entities")

    out_dir   = ROOT / args.output_dir
    clarif_dir = ROOT / args.clarification_dir

    if args.dry_run:
        logger.info("DRY-RUN: structural inputs validated; no files written")
        return 0

    # Generate from the corrected input, then validate the resulting rules.
    result = subprocess.run([sys.executable, str(ROOT / "build_phase6_7.py")], cwd=ROOT)
    if result.returncode:
        logger.error("Compatibility generation pipeline failed.")
        return result.returncode

    # Load generated rules
    rules_path = out_dir / "compatibility_rule_candidates.json"
    if not rules_path.exists():
        logger.error(f"Generated rules not found: {rules_path}")
        logger.error("Run 'python build_phase6_7.py' first.")
        return 1

    rules_data = json.loads(rules_path.read_text(encoding="utf-8"))
    rules = rules_data.get("rules", [])
    logger.info(f"Validating {len(rules)} generated rules")

    valid = validate_generated_rules(rules, logger)
    if not valid:
        logger.error("Validation failed - see errors above")
        return 1

    logger.info(f"Validation PASSED for {len(rules)} rules")

    # Verify key invariants on clarification output
    clarif_path = clarif_dir / "compatibility_rules_needing_clarification.json"
    if clarif_path.exists():
        clarif_data = json.loads(clarif_path.read_text(encoding="utf-8"))
        logger.info(f"Clarification items: {clarif_data.get('source_candidate_count', 0)}")

    logger.info("Phase 7 generation artifacts verified.")
    logger.info(f"Rules: {rules_path}")
    logger.info(f"Clarification: {clarif_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
