"""
Evidence Graph Builder — assembles a temporary in-memory graph from
a list of Evidence objects.

The graph is a dict with:
  nodes: {node_id: {type, label, properties}}
  edges: [{from, to, relationship, weight}]

Example graph for "Why is Laptop001 non-compliant?":
  Laptop001 --[HAS_FIRMWARE]--> Firmware 3.2
  Firmware 3.2 --[VIOLATES]--> VersionConstraint >=3.5
  VersionConstraint >=3.5 --[REQUIRED_BY]--> BIOS 2.1
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List

try:
    from .models.evidence_models import Evidence
except ImportError:
    from models.evidence_models import Evidence

logger = logging.getLogger(__name__)


def _node_id(label: str) -> str:
    return "N-" + hashlib.md5(label.encode()).hexdigest()[:8].upper()


class EvidenceGraphBuilder:
    """Build a lightweight evidence graph from a ranked evidence list."""

    def build(self, evidence: List[Evidence]) -> Dict[str, Any]:
        nodes: Dict[str, Dict] = {}
        edges: List[Dict]      = []
        edge_keys: set         = set()

        for e in evidence:
            # Primary node (entity)
            nid = _node_id(e.entity)
            if nid not in nodes:
                nodes[nid] = {
                    "node_id":    nid,
                    "type":       e.evidence_type,
                    "label":      e.entity,
                    "properties": {"source_layer": e.source_layer,
                                   "confidence":   e.confidence}
                }

            # Secondary node (target) + edge
            if e.relationship and e.target:
                tid = _node_id(e.target)
                if tid not in nodes:
                    nodes[tid] = {
                        "node_id":    tid,
                        "type":       "TargetNode",
                        "label":      e.target,
                        "properties": {}
                    }
                edge_key = (nid, e.relationship, tid)
                if edge_key not in edge_keys:
                    edge_keys.add(edge_key)
                    edges.append({
                        "from":         nid,
                        "to":           tid,
                        "relationship": e.relationship,
                        "weight":       round(e.confidence, 3),
                        "evidence_id":  e.evidence_id,
                    })

        graph = {
            "node_count": len(nodes),
            "edge_count":  len(edges),
            "nodes":       list(nodes.values()),
            "edges":       edges,
        }
        logger.debug("Built evidence graph: %d nodes, %d edges",
                     len(nodes), len(edges))
        return graph
