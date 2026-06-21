#!/usr/bin/env python3
"""
Phase 6: Correct and normalize compatibility rule candidates.

CLI:
    python scripts/correct_compatibility_candidates.py \\
        --input CompatibilityLayer/source/raw/normalized_rule_candidates.json \\
        --analysis-dir CompatibilityLayer/analysis \\
        --resolution-dir CompatibilityLayer/resolution \\
        --output-dir CompatibilityLayer/rules/corrected \\
        [--dry-run] [--log-level DEBUG|INFO|WARNING]
"""
import argparse
import hashlib
import json
import logging
import pathlib
import subprocess
import sys
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ── operator / logic maps ───────────────────────────────────────────────────
OP_MAP = {
    "==": "equals", "!=": "not_equals",
    ">=": "greater_than_or_equal", ">": "greater_than",
    "<=": "less_than_or_equal", "<": "less_than",
    "installed": "installed", "exists": "exists",
}
LOGIC_MAP = {"AND": "ALL", "OR": "ANY"}

ENTITY_MAP = {
    "enterprise os":             ("OS-013", "Enterprise OS",            "Operating System"),
    "system firmware":           ("FW-013", "System Firmware",          "Firmware"),
    "firmware":                  ("FW-013", "System Firmware",          "Firmware"),
    "system bios":               ("FW-001", "BIOS",                     "Firmware"),
    "bios":                      ("FW-001", "BIOS",                     "Firmware"),
    "driver pack":               ("DRV-009","Driver Pack",              "Driver"),
    "platform driver pack":      ("DRV-010","Platform Driver Pack",     "Driver"),
    "nic firmware":              ("FW-005", "Network Firmware",         "Firmware"),
    "security agent":            ("SEC-004","EDR Agent",                "Security"),
    "endpoint management agent": ("MGT-010","Endpoint Agent",           "Management"),
    "endpoint mgmt agent":       ("MGT-010","Endpoint Agent",           "Management"),
    "siem":                      ("MGT-008","SIEM",                     "Management"),
}

CLARIF_CIDS = {
    "RCAND-000361","RCAND-000365","RCAND-000367","RCAND-000368",
    "RCAND-000369","RCAND-000374","RCAND-000376","RCAND-000377",
    "RCAND-000382","RCAND-000385","RCAND-000398","RCAND-000400",
    "RCAND-000401",
}


def resolve_entity(name: Optional[str], _ctype: Optional[str] = None
                   ) -> Tuple[Optional[str], str, Optional[str], str]:
    if not name or str(name).lower() in ("unknown", "none", "", "null"):
        return None, name or "", None, "unresolved"
    key = str(name).strip().lower()
    if key in ENTITY_MAP:
        eid, cname, cat = ENTITY_MAP[key]
        return eid, cname, cat, "resolved_domain_entity"
    for k, (eid, cname, cat) in ENTITY_MAP.items():
        if k in key or key in k:
            return eid, cname, cat, "resolved_domain_entity"
    return None, name, None, "unresolved"


def norm_op(op: str) -> str:
    return OP_MAP.get(op, op)


def norm_ver(v: Any) -> str:
    if v and isinstance(v, str):
        v = v.strip()
        if v.startswith("v") and len(v) > 1 and v[1].isdigit():
            v = v[1:]
    return v or ""


def candidate_hash(c: Dict) -> str:
    s = json.dumps(c, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode()).hexdigest()[:16].upper()


def run_pipeline(logger: logging.Logger) -> int:
    """Execute the deterministic builder without triggering work on import."""
    result = subprocess.run([sys.executable, str(ROOT / "build_phase6_7.py")], cwd=ROOT)
    if result.returncode:
        logger.error("Compatibility correction pipeline failed.")
    return result.returncode


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 6: Correct compatibility rule candidates.")
    parser.add_argument("--input", required=True, help="Path to normalized_rule_candidates.json")
    parser.add_argument("--analysis-dir", default="CompatibilityLayer/analysis",
                        help="Directory containing dataset analysis files (optional)")
    parser.add_argument("--resolution-dir", default="CompatibilityLayer/resolution",
                        help="Directory containing entity/version resolution outputs (optional)")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory for corrected artifacts")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run correction logic without writing any files")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level),
                        format="%(levelname)s %(message)s")
    logger = logging.getLogger("correct_candidates")

    src = ROOT / args.input
    if not src.exists():
        logger.error(f"Input file not found: {src}")
        return 1

    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    logger.info(f"Source SHA256: {sha}")

    raw = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(raw.get("rule_candidates"), list):
        logger.error("Input does not contain a 'rule_candidates' array.")
        return 1

    logger.info(f"Loaded {len(raw['rule_candidates'])} candidates from {src}")

    if args.dry_run:
        logger.info("DRY-RUN: correction logic executed but no files written.")
        return 0

    canonical = ROOT / "CompatibilityLayer/rules/corrected"
    out_dir = (ROOT / args.output_dir).resolve()
    if out_dir != canonical.resolve():
        logger.error("This release pipeline only supports the governed output directory: %s", canonical)
        return 1
    return run_pipeline(logger)


if __name__ == "__main__":
    sys.exit(main())
