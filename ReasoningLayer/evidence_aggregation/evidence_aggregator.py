"""
Evidence Aggregator — combines collector output into a unified
EvidencePackage consumed by downstream reasoning engines.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from .evidence_collector   import EvidenceCollector
    from .evidence_ranker      import EvidenceRanker
    from .evidence_graph_builder import EvidenceGraphBuilder
    from .models.evidence_models import Evidence, EvidencePackage
except ImportError:
    from evidence_collector    import EvidenceCollector
    from evidence_ranker       import EvidenceRanker
    from evidence_graph_builder import EvidenceGraphBuilder
    from models.evidence_models import Evidence, EvidencePackage

logger = logging.getLogger(__name__)


def _query_id(question: str) -> str:
    h = hashlib.md5(question.encode()).hexdigest()[:12].upper()
    return f"QID-{h}"


class EvidenceAggregator:
    """Produce a unified EvidencePackage from a Query Understanding query plan."""

    def __init__(self,
                 collector: Optional[EvidenceCollector] = None,
                 ranker:    Optional[EvidenceRanker]    = None,
                 builder:   Optional[EvidenceGraphBuilder] = None,
                 offline:   bool = False) -> None:
        self.collector = collector or EvidenceCollector(offline=offline)
        self.ranker    = ranker    or EvidenceRanker()
        self.builder   = builder   or EvidenceGraphBuilder()

    def aggregate(self, query_plan: Dict[str, Any]) -> EvidencePackage:
        """
        Full pipeline:
          1. Collect evidence from all routed layers.
          2. Rank by priority.
          3. Build evidence graph.
          4. Return EvidencePackage.
        """
        question = query_plan.get("question", "")
        intent   = query_plan.get("intent", "")
        entities_raw = query_plan.get("entities", {})
        qid = _query_id(question)

        # 1. collect
        raw_evidence = self.collector.collect(query_plan)

        # 2. rank
        ranked = self.ranker.rank(list(raw_evidence))

        # 3. graph
        graph = self.builder.build(ranked)

        # 4. entity list for the package
        entity_list = []
        if entities_raw.get("device"):
            entity_list.append({"entity_type": "Device",
                                 "entity_id":   entities_raw["device"]})
        for key in ("bios","firmware","operating_system","driver",
                    "security_component","management_tool"):
            if entities_raw.get(key):
                entity_list.append({"entity_type": key,
                                    "version":     entities_raw[key]})

        pkg = EvidencePackage(
            query_id        = qid,
            intent          = intent,
            question        = question,
            entities        = entity_list,
            evidence        = raw_evidence,
            ranked_evidence = ranked,
            evidence_graph  = graph,
            metadata        = {
                "target_layers": query_plan.get("target_layers", []),
                "evidence_count": len(raw_evidence),
                "ranked_count":   len(ranked),
                "generated_at":   datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("Aggregated package qid=%s intent=%s evidence=%d",
                    qid, intent, len(raw_evidence))
        return pkg
