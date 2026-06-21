"""
Neo4j-based retriever for Layer 2 inventory evidence.

When Neo4j is offline the retriever returns empty lists and logs a warning.
All public methods are safe to call in offline / unit-test mode.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from .connectors.neo4j_connector import Neo4jConnector
    from .models.evidence_models import Evidence
except ImportError:
    from connectors.neo4j_connector import Neo4jConnector
    from models.evidence_models import Evidence

logger = logging.getLogger(__name__)


class Neo4jRetriever:
    """Retrieve device inventory evidence from Neo4j."""

    def __init__(self, connector: Optional[Neo4jConnector] = None,
                 offline: bool = False) -> None:
        self.connector = connector or Neo4jConnector(offline=offline)
        self.offline   = offline or not self.connector.available

    # ── device ────────────────────────────────────────────────────────────

    def get_device(self, device_id: str) -> List[Evidence]:
        """Retrieve top-level device node and properties."""
        rows = self.connector.run(
            "MATCH (d:Device {device_id: $id}) RETURN d",
            {"id": device_id})
        return [self._device_evidence(r.get("d", {}), device_id) for r in rows]

    # ── installed components ───────────────────────────────────────────────

    def get_installed_bios(self, device_id: str) -> List[Evidence]:
        rows = self.connector.run(
            "MATCH (d:Device {device_id: $id})-[:HAS_BIOS]->(b:BIOS) RETURN b",
            {"id": device_id})
        return [self._component_evidence(r.get("b", {}), device_id, "BIOS", "HAS_BIOS")
                for r in rows]

    def get_installed_firmware(self, device_id: str) -> List[Evidence]:
        rows = self.connector.run(
            "MATCH (d:Device {device_id: $id})-[:HAS_FIRMWARE]->(f:Firmware) RETURN f",
            {"id": device_id})
        return [self._component_evidence(r.get("f", {}), device_id, "Firmware", "HAS_FIRMWARE")
                for r in rows]

    def get_installed_os(self, device_id: str) -> List[Evidence]:
        rows = self.connector.run(
            "MATCH (d:Device {device_id: $id})-[:HAS_OS]->(o:OperatingSystem) RETURN o",
            {"id": device_id})
        return [self._component_evidence(r.get("o", {}), device_id, "OperatingSystem", "HAS_OS")
                for r in rows]

    def get_installed_drivers(self, device_id: str) -> List[Evidence]:
        rows = self.connector.run(
            "MATCH (d:Device {device_id: $id})-[:HAS_DRIVER]->(dr:Driver) RETURN dr",
            {"id": device_id})
        return [self._component_evidence(r.get("dr", {}), device_id, "Driver", "HAS_DRIVER")
                for r in rows]

    def get_installed_security_agents(self, device_id: str) -> List[Evidence]:
        rows = self.connector.run(
            "MATCH (d:Device {device_id:$id})-[:HAS_SECURITY_AGENT]->(s:SecurityAgent) RETURN s",
            {"id": device_id})
        return [self._component_evidence(r.get("s", {}), device_id, "SecurityAgent", "HAS_SECURITY_AGENT")
                for r in rows]

    def get_installed_management_agents(self, device_id: str) -> List[Evidence]:
        rows = self.connector.run(
            "MATCH (d:Device {device_id:$id})-[:HAS_MANAGEMENT_AGENT]->(m:ManagementAgent) RETURN m",
            {"id": device_id})
        return [self._component_evidence(r.get("m", {}), device_id, "ManagementAgent", "HAS_MANAGEMENT_AGENT")
                for r in rows]

    def get_device_relationships(self, device_id: str) -> List[Evidence]:
        """Return all relationships for a device — compatibility, compliance, violations."""
        rows = self.connector.run(
            "MATCH (d:Device {device_id: $id})-[r]-(n) RETURN type(r) AS rel, n",
            {"id": device_id})
        evidence = []
        for row in rows:
            target = row.get("n", {})
            evidence.append(Evidence(
                evidence_type="InventoryEvidence",
                source_layer="Layer2",
                source_system="Neo4j",
                entity=device_id,
                relationship=row.get("rel"),
                target=str(target.get("id") or target.get("name", "")),
                confidence=1.0,
                content=dict(target),
                metadata={"device_id": device_id}
            ))
        return evidence

    def get_fleet_devices(self, limit: int = 100) -> List[Evidence]:
        """Return real device inventory for fleet-level questions."""
        rows = self.connector.run(
            "MATCH (d:Device) RETURN d ORDER BY d.device_id LIMIT $limit",
            {"limit": int(limit)},
        )
        evidence = []
        for row in rows:
            node = dict(row.get("d", {}))
            device_id = str(node.get("device_id") or node.get("id") or node.get("name") or "")
            if device_id:
                evidence.append(self._device_evidence(node, device_id))
        return evidence

    # ── builders ──────────────────────────────────────────────────────────

    def _device_evidence(self, node: Dict, device_id: str) -> Evidence:
        return Evidence(
            evidence_type="InventoryEvidence",
            source_layer="Layer2",
            source_system="Neo4j",
            entity=device_id,
            confidence=1.0,
            content=dict(node),
            metadata={"node_type": "Device", "device_id": device_id}
        )

    def _component_evidence(self, node: Dict, device_id: str,
                            component_type: str, relationship: str) -> Evidence:
        return Evidence(
            evidence_type="InventoryEvidence",
            source_layer="Layer2",
            source_system="Neo4j",
            entity=device_id,
            relationship=relationship,
            target=str(node.get("version") or node.get("name") or component_type),
            confidence=1.0,
            content={"component_type": component_type, **dict(node)},
            metadata={"device_id": device_id, "component_type": component_type}
        )

    # ── connectivity ──────────────────────────────────────────────────────

    @property
    def neo4j_available(self) -> bool:
        return self.connector.available
