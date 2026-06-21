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
        return self._get_components_by_type(device_id, "bios")

    def get_installed_firmware(self, device_id: str) -> List[Evidence]:
        return self._get_components_by_type(device_id, "firmware")

    def get_installed_os(self, device_id: str) -> List[Evidence]:
        return self._get_components_by_type(device_id, "os")

    def get_installed_drivers(self, device_id: str) -> List[Evidence]:
        return self._get_components_by_type(device_id, "driver")

    def get_installed_security_agents(self, device_id: str) -> List[Evidence]:
        return self._get_components_by_type(device_id, "agent")

    def get_installed_management_agents(self, device_id: str) -> List[Evidence]:
        return self._get_components_by_type(device_id, "management_tool")

    def get_installed_tpm(self, device_id: str) -> List[Evidence]:
        return self._get_components_by_type(device_id, "tpm")

    def _get_components_by_type(self, device_id: str, component_type: str) -> List[Evidence]:
        """Generic helper to retrieve components of a specific type under the new schema."""
        if self.offline:
            return []
        
        query = """
        MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)
        WHERE c.component_type = $ctype
        OPTIONAL MATCH (c)-[:INSTANCE_OF]->(e:Entity)
        RETURN c {
            .*,
            entity_name: e.name,
            entity_id: e.entity_id
        } AS comp
        """
        rows = self.connector.run(query, {"id": device_id, "ctype": component_type})
        evidence = []
        for r in rows:
            comp_data = dict(r.get("comp") or {})
            
            # Ensure required keys are explicitly present (even if None)
            comp_data.setdefault("component_name", None)
            comp_data.setdefault("component_type", component_type)
            comp_data.setdefault("version_raw", None)
            comp_data.setdefault("version_normalized", None)
            comp_data.setdefault("vendor", None)
            comp_data.setdefault("entity_name", None)
            comp_data.setdefault("entity_id", None)
            
            evidence.append(self._component_evidence(
                comp_data,
                device_id,
                component_type,
                "HAS_COMPONENT"
            ))
        return evidence

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
        # Fallback resolution for target property of Evidence
        target_val = (
            node.get("version_normalized") or
            node.get("version_raw") or
            node.get("version") or
            node.get("component_name") or
            node.get("name") or
            component_type
        )
        return Evidence(
            evidence_type="InventoryEvidence",
            source_layer="Layer2",
            source_system="Neo4j",
            entity=device_id,
            relationship=relationship,
            target=str(target_val),
            confidence=1.0,
            content={"component_type": component_type, **dict(node)},
            metadata={"device_id": device_id, "component_type": component_type}
        )

    # ── connectivity ──────────────────────────────────────────────────────

    @property
    def neo4j_available(self) -> bool:
        return self.connector.available
