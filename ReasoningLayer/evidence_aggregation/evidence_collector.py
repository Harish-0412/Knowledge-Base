"""
Evidence Collector — orchestrates retrieval from all three layers
given a structured query plan produced by the Query Understanding Layer.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from .qdrant_retriever import QdrantRetriever
    from .neo4j_retriever  import Neo4jRetriever
    from .models.evidence_models import Evidence
except ImportError:
    from qdrant_retriever import QdrantRetriever
    from neo4j_retriever  import Neo4jRetriever
    from models.evidence_models import Evidence

logger = logging.getLogger(__name__)


class EvidenceCollector:
    """Collect evidence from Layer 1, Layer 2, and Layer 3 for a query plan."""

    def __init__(self,
                 qdrant: Optional[QdrantRetriever] = None,
                 neo4j:  Optional[Neo4jRetriever]  = None,
                 offline: bool = False) -> None:
        self.qdrant  = qdrant or QdrantRetriever(offline=offline)
        self.neo4j   = neo4j  or Neo4jRetriever(offline=offline)

    def collect(self, query_plan: Dict[str, Any]) -> List[Evidence]:
        """
        Main entry point.  Accepts the dict produced by QueryUnderstandingService
        and returns a flat list of Evidence objects, deduplicated by evidence_id.
        """
        evidence: List[Evidence] = []
        layers  = set(query_plan.get("target_layers", []))
        intent  = query_plan.get("intent", "")
        entities= query_plan.get("entities", {})
        question= query_plan.get("question", "")

        if "Layer1" in layers:
            evidence.extend(self._collect_domain(question, entities))

        if "Layer2" in layers:
            evidence.extend(self._collect_inventory(entities, intent))

        if "Layer3" in layers:
            evidence.extend(self._collect_compatibility(question, entities))

        # deduplicate by evidence_id (keep first occurrence)
        seen: set = set()
        deduped: List[Evidence] = []
        for e in evidence:
            if e.evidence_id not in seen:
                seen.add(e.evidence_id)
                deduped.append(e)

        logger.info("Collected %d evidence items (after dedup) for intent=%s",
                    len(deduped), intent)
        return deduped

    # ── Layer 1 ───────────────────────────────────────────────────────────

    def _collect_domain(self, question: str,
                        entities: Dict[str, Any]) -> List[Evidence]:
        evidence: List[Evidence] = []
        # semantic search on the question
        evidence.extend(self.qdrant.search_domain(question, limit=5))
        # entity-specific lookup for every named component
        component_types = entities.get("component_types", [])
        for ctype in component_types:
            evidence.extend(self.qdrant.retrieve_by_entity(ctype, limit=3))
        # direct component keys
        for key in ("bios", "firmware", "operating_system", "driver",
                    "security_component", "management_tool"):
            val = entities.get(key)
            if val:
                evidence.extend(self.qdrant.retrieve_by_entity(key, limit=3))
        return evidence

    # ── Layer 2 ───────────────────────────────────────────────────────────

    def _collect_inventory(self, entities: Dict[str, Any], intent: str = "") -> List[Evidence]:
        evidence: List[Evidence] = []
        device_id = entities.get("device")
        if not device_id:
            return self.neo4j.get_fleet_devices() if intent == "FleetAnalysis" else evidence
        evidence.extend(self.neo4j.get_device(device_id))
        evidence.extend(self.neo4j.get_installed_bios(device_id))
        evidence.extend(self.neo4j.get_installed_firmware(device_id))
        evidence.extend(self.neo4j.get_installed_os(device_id))
        evidence.extend(self.neo4j.get_installed_drivers(device_id))
        evidence.extend(self.neo4j.get_installed_security_agents(device_id))
        evidence.extend(self.neo4j.get_installed_management_agents(device_id))
        evidence.extend(self.neo4j.get_device_relationships(device_id))
        return evidence

    # ── Layer 3 ───────────────────────────────────────────────────────────

    def _collect_compatibility(self, question: str,
                               entities: Dict[str, Any]) -> List[Evidence]:
        evidence: List[Evidence] = []
        evidence.extend(self.qdrant.search_compatibility(question, limit=10))
        rule_id = entities.get("rule")
        if rule_id:
            evidence.extend(self.qdrant.retrieve_by_rule(rule_id))
        for key in ("bios", "firmware", "operating_system", "driver"):
            version = entities.get(key)
            if version:
                evidence.extend(
                    self.qdrant.retrieve_by_version(key, version))
        return evidence
