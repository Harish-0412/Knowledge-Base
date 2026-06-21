"""Pure-Python evidence data models — no external dependencies."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

EVIDENCE_TYPES = {
    "InventoryEvidence","CompatibilityEvidence","DomainEvidence",
    "DependencyEvidence","VersionEvidence","LifecycleEvidence",
    "ViolationEvidence","RecommendationEvidence","RiskEvidence",
}
PRIORITY_SCORES = {"Critical":100,"Highest":85,"High":70,"Medium":50,"Low":25}


def _make_id(evidence_type: str, entity: str, content: Any) -> str:
    prefix = evidence_type[:4].upper()
    payload = json.dumps({"t": evidence_type, "e": entity, "c": str(content)},
                         sort_keys=True)
    h = hashlib.sha256(payload.encode()).hexdigest()[:8].upper()
    return f"EVID-{prefix}-{h}"


@dataclass
class Evidence:
    evidence_type: str
    source_layer:  str
    source_system: str
    entity:        str
    confidence:    float
    content:       Dict[str, Any]       = field(default_factory=dict)
    relationship:  Optional[str]        = None
    target:        Optional[str]        = None
    retrieval_score: Optional[float]    = None
    priority:      Optional[str]        = None
    query_id:      Optional[str]        = None
    metadata:      Dict[str, Any]       = field(default_factory=dict)
    evidence_id:   str                  = field(init=False)
    timestamp:     str                  = field(init=False)

    def __post_init__(self):
        if self.evidence_type not in EVIDENCE_TYPES:
            raise ValueError(f"Unknown evidence_type: {self.evidence_type}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        self.evidence_id = _make_id(self.evidence_type, self.entity, self.content)
        self.timestamp   = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def priority_score(self) -> float:
        base = PRIORITY_SCORES.get(self.priority or "Medium", 50)
        return base * (0.5 + 0.5 * self.confidence)


@dataclass
class EvidencePackage:
    query_id:        str
    intent:          str
    question:        str
    entities:        List[Dict[str, Any]] = field(default_factory=list)
    evidence:        List[Evidence]       = field(default_factory=list)
    ranked_evidence: List[Evidence]       = field(default_factory=list)
    evidence_graph:  Dict[str, Any]       = field(default_factory=dict)
    metadata:        Dict[str, Any]       = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "query_id":        self.query_id,
            "intent":          self.intent,
            "question":        self.question,
            "entities":        self.entities,
            "evidence":        [e.to_dict() for e in self.evidence],
            "ranked_evidence": [e.to_dict() for e in self.ranked_evidence],
            "evidence_graph":  self.evidence_graph,
            "metadata":        self.metadata,
        }
