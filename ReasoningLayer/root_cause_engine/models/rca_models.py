"""Root Cause Analysis data models."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

RISK_SCORES = {"Informational":0,"Low":25,"Medium":50,"High":75,"Critical":100}
VALID_STATUSES = {"open","investigating","resolved","suppressed"}


def _find_id(device: str, root_cause_id: str, violation_id: str) -> str:
    payload = json.dumps({"d":device,"rc":root_cause_id,"v":violation_id}, sort_keys=True)
    return "FIND-" + hashlib.sha256(payload.encode()).hexdigest()[:8].upper()


@dataclass
class RCAFinding:
    query_id:           str
    device:             str
    root_cause_id:      str
    root_cause_name:    str
    violation_id:       str
    violation_name:     str
    risk_level:         str
    description:        str
    affected_component: str
    required_action:    str
    recommendations:    List[str]           = field(default_factory=list)
    evidence_ids:       List[str]           = field(default_factory=list)
    confidence:         float               = 0.8
    status:             str                 = "open"
    metadata:           Dict[str, Any]      = field(default_factory=dict)
    finding_id:         str                 = field(init=False)
    severity_score:     int                 = field(init=False)
    timestamp:          str                 = field(init=False)

    def __post_init__(self):
        if self.risk_level not in RISK_SCORES:
            raise ValueError(f"Invalid risk_level: {self.risk_level}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        self.finding_id    = _find_id(self.device, self.root_cause_id, self.violation_id)
        self.severity_score = RISK_SCORES[self.risk_level]
        self.timestamp     = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RCAReport:
    query_id:        str
    device:          str
    intent:          str
    findings:        List[RCAFinding]      = field(default_factory=list)
    overall_risk:    str                   = "Informational"
    summary:         str                   = ""
    evidence_count:  int                   = 0
    metadata:        Dict[str, Any]        = field(default_factory=dict)

    def __post_init__(self):
        if self.findings:
            top = max(self.findings, key=lambda f: f.severity_score)
            self.overall_risk = top.risk_level

    def to_dict(self) -> dict:
        return {
            "query_id":       self.query_id,
            "device":         self.device,
            "intent":         self.intent,
            "overall_risk":   self.overall_risk,
            "finding_count":  len(self.findings),
            "summary":        self.summary,
            "evidence_count": self.evidence_count,
            "findings":       [f.to_dict() for f in self.findings],
            "metadata":       self.metadata,
        }
