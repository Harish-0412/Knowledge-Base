"""
Root Cause Analyzer — orchestrates detection, assessment, and finding
production for a given EvidencePackage.
"""
from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .violation_detector import ViolationDetector
    from .risk_assessor       import RiskAssessor
    from .models.rca_models   import RCAFinding, RCAReport
except ImportError:
    from violation_detector import ViolationDetector
    from risk_assessor       import RiskAssessor
    from models.rca_models   import RCAFinding, RCAReport

logger = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parent

# Load recommendation lookup
_RC_TYPES = json.loads((BASE.parents[1]/"ReasoningLayer/ontology/root_cause_types.json").read_text(encoding="utf-8"))
_VIOL_TYPES = json.loads((BASE.parents[1]/"ReasoningLayer/ontology/violation_types.json").read_text(encoding="utf-8"))
_REC_TYPES  = json.loads((BASE.parents[1]/"ReasoningLayer/ontology/recommendation_types.json").read_text(encoding="utf-8"))

_RC_MAP   = {r["root_cause_id"]: r for r in _RC_TYPES}
_VIOL_MAP = {v["violation_id"]:  v for v in _VIOL_TYPES}
_REC_MAP  = {r["recommendation_id"]: r["name"] for r in _REC_TYPES}


class RootCauseAnalyzer:
    """Produce an RCAReport from an EvidencePackage dict."""

    def __init__(self,
                 detector: Optional[ViolationDetector] = None,
                 assessor: Optional[RiskAssessor]      = None) -> None:
        self.detector = detector or ViolationDetector()
        self.assessor = assessor or RiskAssessor()

    def analyze(self, evidence_package: Dict[str, Any]) -> RCAReport:
        query_id = evidence_package.get("query_id", "QID-UNKNOWN")
        intent   = evidence_package.get("intent",   "RootCauseAnalysis")
        question = evidence_package.get("question", "")
        entities = evidence_package.get("entities", [])
        evidence = evidence_package.get("ranked_evidence") or evidence_package.get("evidence", [])
        meta     = evidence_package.get("metadata", {})

        # Primary device
        device = "unknown"
        for ent in entities:
            if ent.get("entity_type") == "Device":
                device = ent.get("entity_id", "unknown")
                break
        if device == "unknown":
            # Try extracting from question
            import re
            m = re.search(r"\b(?:Laptop|Device|Server|Endpoint|Workstation)[-_]?[A-Za-z0-9]+\b",
                          question, re.I)
            if m:
                device = m.group(0)

        # Detect
        detections = self.detector.detect(evidence, question)
        # Assess
        assessed = self.assessor.assess(detections, device_count=1)

        # Build findings (deduplicate by finding_id)
        findings: List[RCAFinding] = []
        seen_fids: set = set()
        for rc_id, viol_id, component, risk, conf, label in assessed:
            rc_info   = _RC_MAP.get(rc_id, {})
            viol_info = _VIOL_MAP.get(viol_id, {})
            recs      = [r for r in rc_info.get("recommended_actions", [])]
            primary   = recs[0] if recs else "REC-MONITORING-ACTION"
            primary_label = _REC_MAP.get(primary, primary)

            finding = RCAFinding(
                query_id           = query_id,
                device             = device,
                root_cause_id      = rc_id,
                root_cause_name    = rc_info.get("name", rc_id),
                violation_id       = viol_id,
                violation_name     = viol_info.get("name", viol_id),
                risk_level         = risk,
                description        = rc_info.get("description",
                                    f"{label} detected on {device}"),
                affected_component = component,
                required_action    = primary_label,
                recommendations    = recs,
                evidence_ids       = [e.get("evidence_id","") for e in evidence[:5]
                                      if e.get("evidence_id","")],
                confidence         = conf,
                status             = "open",
                metadata           = {"detection_label": label,
                                      "source_layers":
                                      list({e.get("source_layer","") for e in evidence})},
            )
            if finding.finding_id not in seen_fids:
                seen_fids.add(finding.finding_id)
                findings.append(finding)

        # Summary
        if findings:
            top = max(findings, key=lambda f: f.severity_score)
            summary = (f"Analysis of {device}: {len(findings)} finding(s). "
                       f"Highest risk: {top.risk_level} — {top.root_cause_name}.")
        else:
            summary = (f"No violations detected for {device}. "
                       "Evidence may be insufficient; manual review recommended.")
            # Add an informational finding when no issues found
            findings.append(RCAFinding(
                query_id=query_id, device=device,
                root_cause_id="RC-UNKNOWN-STATE", root_cause_name="UnknownState",
                violation_id="VIOL-COMPLIANCE", violation_name="ComplianceViolation",
                risk_level="Informational",
                description="No violation evidence detected. Insufficient or offline evidence.",
                affected_component=device, required_action="MonitoringAction",
                recommendations=["REC-MONITORING-ACTION"], confidence=0.5,
                metadata={"note": "offline_mode_or_no_evidence"}
            ))

        report = RCAReport(
            query_id=query_id, device=device, intent=intent,
            findings=findings, summary=summary,
            evidence_count=len(evidence),
            metadata={"query": question, "layers": meta.get("target_layers",[])}
        )
        logger.info("RCA complete: device=%s findings=%d overall_risk=%s",
                    device, len(findings), report.overall_risk)
        return report
