"""
Violation Detector — inspects an EvidencePackage and produces
a list of (root_cause_id, violation_id, affected_component, risk_level, confidence)
tuples for the downstream RCAAnalyzer.
"""
from __future__ import annotations
import json, logging, re
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parent

# Map evidence clues to (root_cause_id, violation_id, risk)
_PATTERNS: List[Tuple[str, str, str, str, str]] = [
    # (signal_keyword, root_cause_id, violation_id, default_risk, label)
    ("version mismatch",       "RC-VERSION-MISMATCH",        "VIOL-VERSION",        "High",   "VersionMismatch"),
    ("not supported",          "RC-UNSUPPORTED-CONFIGURATION","VIOL-COMPATIBILITY",  "High",   "UnsupportedConfig"),
    ("incompatible",           "RC-CONFLICT-VIOLATION",      "VIOL-CONFLICT",       "High",   "Conflict"),
    ("conflicts",              "RC-CONFLICT-VIOLATION",      "VIOL-CONFLICT",       "High",   "Conflict"),
    ("missing",                "RC-MISSING-DEPENDENCY",      "VIOL-DEPENDENCY",     "High",   "MissingDependency"),
    ("dependency",             "RC-MISSING-DEPENDENCY",      "VIOL-DEPENDENCY",     "Medium", "Dependency"),
    ("upgrade",                "RC-INVALID-UPGRADE-PATH",    "VIOL-UPGRADE",        "High",   "UpgradePath"),
    ("end-of-support",         "RC-DEPRECATED-COMPONENT",    "VIOL-LIFECYCLE",      "High",   "EndOfSupport"),
    ("end of support",         "RC-DEPRECATED-COMPONENT",    "VIOL-LIFECYCLE",      "High",   "EndOfSupport"),
    ("deprecated",             "RC-DEPRECATED-COMPONENT",    "VIOL-LIFECYCLE",      "Medium", "Deprecated"),
    ("security",               "RC-SECURITY-VIOLATION",      "VIOL-SECURITY",       "Critical","SecurityViolation"),
    ("vulnerability",          "RC-SECURITY-VIOLATION",      "VIOL-SECURITY",       "Critical","SecurityViolation"),
    ("cve",                    "RC-SECURITY-VIOLATION",      "VIOL-SECURITY",       "Critical","SecurityViolation"),
    ("privilege escalation",   "RC-SECURITY-VIOLATION",      "VIOL-SECURITY",       "Critical","SecurityViolation"),
    ("token exposure",         "RC-SECURITY-VIOLATION",      "VIOL-SECURITY",       "Critical","SecurityViolation"),
    ("policy",                 "RC-POLICY-VIOLATION",        "VIOL-POLICY",         "Medium", "PolicyViolation"),
    ("drift",                  "RC-CONFIGURATION-DRIFT",     "VIOL-COMPLIANCE",     "Medium", "ConfigDrift"),
    ("compliance",             "RC-POLICY-VIOLATION",        "VIOL-COMPLIANCE",     "Medium", "Compliance"),
    ("non-compliant",          "RC-POLICY-VIOLATION",        "VIOL-COMPLIANCE",     "High",   "NonCompliant"),
    ("noncompliant",           "RC-POLICY-VIOLATION",        "VIOL-COMPLIANCE",     "High",   "NonCompliant"),
    ("readiness",              "RC-INVALID-UPGRADE-PATH",    "VIOL-UPGRADE",        "High",   "Readiness"),
    ("sequence",               "RC-INVALID-UPGRADE-PATH",    "VIOL-UPGRADE",        "High",   "Sequence"),
    ("order",                  "RC-INVALID-UPGRADE-PATH",    "VIOL-UPGRADE",        "High",   "UpdateOrder"),
    ("unknown",                "RC-UNKNOWN-STATE",           "VIOL-COMPLIANCE",     "Medium", "UnknownState"),
    ("failing",                "RC-VERSION-MISMATCH",        "VIOL-COMPATIBILITY",  "High",   "VersionMismatch"),
    ("fail",                   "RC-VERSION-MISMATCH",        "VIOL-COMPATIBILITY",  "High",   "VersionMismatch"),
    ("lifecycle",              "RC-LIFECYCLE-MISMATCH",      "VIOL-LIFECYCLE",      "Medium", "LifecycleMismatch"),
    ("outdated",               "RC-VERSION-MISMATCH",        "VIOL-VERSION",        "High",   "Outdated"),
    ("boot delay",             "RC-UNSUPPORTED-CONFIGURATION","VIOL-CONFLICT",      "High",   "BootDelay"),
    ("boot failure",           "RC-UNSUPPORTED-CONFIGURATION","VIOL-CONFLICT",      "Critical","BootFailure"),
    ("instability",            "RC-CONFLICT-VIOLATION",      "VIOL-CONFLICT",       "High",   "Instability"),
    ("network adapter",        "RC-CONFLICT-VIOLATION",      "VIOL-CONFLICT",       "High",   "NetworkAdapter"),
    ("telemetry",              "RC-CONFIGURATION-DRIFT",     "VIOL-COMPLIANCE",     "Medium", "Telemetry"),
    ("authentication",         "RC-SECURITY-VIOLATION",      "VIOL-SECURITY",       "Critical","Authentication"),
]

# Severity override when source evidence carries "critical" or "warning" markers
_SEV_WORDS = {"critical":"Critical","warning":"High","info":"Medium","informational":"Informational"}


def _pick_severity(text: str, default: str) -> str:
    for kw, level in _SEV_WORDS.items():
        if re.search(rf"\b{kw}\b", text, re.I):
            return level
    return default


Detection = Tuple[str, str, str, str, float, str]   # (rc_id, viol_id, component, risk, conf, label)


class ViolationDetector:
    """Detect violations from evidence text and type signals."""

    def detect(self, evidence_list: List[Dict[str, Any]], query_text: str = "") -> List[Detection]:
        detections: List[Detection] = []
        seen: set = set()

        search_corpus = [query_text] + [
            e.get("content", {}).get("source_excerpt", "")
            + " " + e.get("content", {}).get("description", "")
            + " " + str(e.get("content", {}).get("rule_type", ""))
            + " " + str(e.get("entity", ""))
            + " " + str(e.get("relationship", ""))
            for e in evidence_list
        ]
        combined = " ".join(search_corpus).lower()

        # Evidence-type based detections (highest fidelity)
        for e in evidence_list:
            etype = e.get("evidence_type", "")
            component = e.get("entity", "") or e.get("target", "") or "unknown"
            conf = float(e.get("confidence", 0.8))
            if etype == "ViolationEvidence":
                key = ("RC-VERSION-MISMATCH","VIOL-VERSION",component)
                if key not in seen:
                    seen.add(key)
                    risk = _pick_severity(str(e.get("content",{})), "High")
                    detections.append(("RC-VERSION-MISMATCH","VIOL-VERSION",component,risk,conf,"ViolationEvidence"))
            elif etype == "RiskEvidence":
                key = ("RC-UNKNOWN-STATE","VIOL-COMPLIANCE",component)
                if key not in seen:
                    seen.add(key)
                    detections.append(("RC-UNKNOWN-STATE","VIOL-COMPLIANCE",component,"High",conf,"RiskEvidence"))

        # Keyword-based detections on combined text
        for signal, rc_id, viol_id, default_risk, label in _PATTERNS:
            if signal in combined:
                # find the most relevant component
                component = "device"
                for e in evidence_list:
                    ent = e.get("entity","")
                    if ent and ent.lower() not in ("device","unknown",""):
                        component = ent
                        break
                risk = _pick_severity(combined, default_risk)
                key = (rc_id, viol_id, component)
                if key not in seen:
                    seen.add(key)
                    conf = 0.75
                    detections.append((rc_id, viol_id, component, risk, conf, label))

        logger.debug("ViolationDetector: %d detections", len(detections))
        return detections
