"""
Recommendation Engine — enriches RCA findings with ordered,
human-readable recommendations drawn from the reasoning ontology.
"""
from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
BASE = Path(__file__).resolve().parent

_REC_TYPES = json.loads(
    (BASE.parents[1]/"ReasoningLayer/ontology/recommendation_types.json")
    .read_text(encoding="utf-8"))
_REC_MAP = {r["recommendation_id"]: r for r in _REC_TYPES}

_PRIORITY_MAP = {
    "Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Informational": 4
}


class RecommendationEngine:
    """Produce ordered recommendation objects for an RCA report."""

    def enrich(self, report_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add enriched recommendations to each finding in-place."""
        for finding in report_dict.get("findings", []):
            recs = finding.get("recommendations", [])
            enriched = []
            for rec_id in recs:
                info = _REC_MAP.get(rec_id, {})
                enriched.append({
                    "recommendation_id": rec_id,
                    "name":        info.get("name", rec_id),
                    "description": info.get("description",""),
                    "priority":    _PRIORITY_MAP.get(finding.get("risk_level","Low"), 3),
                })
            finding["enriched_recommendations"] = enriched
        return report_dict
