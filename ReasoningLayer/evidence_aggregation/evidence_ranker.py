"""
Evidence Ranker — assigns priority scores and produces a ranked list.

Priority matrix (from evidence_priority_matrix.json):
  ViolationEvidence / RiskEvidence      -> Critical  (score 100)
  InventoryEvidence                     -> Highest   (score  85)
  CompatibilityEvidence / VersionEvidence
  DependencyEvidence / RecommendationEvidence -> High (score 70)
  DomainEvidence / LifecycleEvidence    -> Medium   (score  50)
  Background DomainEvidence             -> Low      (score  25)

Final score = base_score * (0.5 + 0.5 * confidence)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

try:
    from .models.evidence_models import Evidence, PRIORITY_SCORES
except ImportError:
    from models.evidence_models import Evidence, PRIORITY_SCORES

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

_TYPE_PRIORITY = {
    "ViolationEvidence":     "Critical",
    "RiskEvidence":          "Critical",
    "InventoryEvidence":     "Highest",
    "CompatibilityEvidence": "High",
    "VersionEvidence":       "High",
    "DependencyEvidence":    "High",
    "RecommendationEvidence":"High",
    "LifecycleEvidence":     "Medium",
    "DomainEvidence":        "Medium",
}


class EvidenceRanker:
    """Assign priority and sort evidence by final score descending."""

    def rank(self, evidence: List[Evidence]) -> List[Evidence]:
        for e in evidence:
            priority = _TYPE_PRIORITY.get(e.evidence_type, "Medium")
            e.priority = priority
        ranked = sorted(evidence, key=lambda e: e.priority_score, reverse=True)
        logger.debug("Ranked %d evidence items; top priority=%s",
                     len(ranked), ranked[0].priority if ranked else "n/a")
        return ranked
