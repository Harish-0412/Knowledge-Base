# file: ComplianceEngine/rule_matcher.py
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ReasoningLayer.evidence_aggregation.connectors.neo4j_connector import Neo4jConnector

logger = logging.getLogger(__name__)

class RuleMatcher:
    """Matches CompatibilityRules applicable to a Device's installed ComponentInstances."""
    
    def __init__(self, connector: Optional[Neo4jConnector] = None) -> None:
        self.connector = connector or Neo4jConnector()

    def match_rules_for_device(self, device_id: str) -> Dict[str, Any]:
        """
        Finds all compatibility rules applicable to the given device.
        
        Steps:
        1. Retrieve ComponentInstances connected to the Device.
        2. Follow INSTANCE_OF to Entity.
        3. Find CompatibilityRules targeting those entities.
        """
        if not device_id:
            return {"device_id": "", "matched_rules": []}

        query = """
        MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)-[:INSTANCE_OF]->(e:Entity)
        MATCH (r:CompatibilityRule)-[:TARGETS]->(e)
        OPTIONAL MATCH (r)-[:HAS_CONSTRAINT]->(vc:VersionConstraint)
        RETURN r.rule_id AS rule_id,
               r.predicate AS predicate,
               r.severity AS severity,
               e.entity_id AS target_entity,
               CASE WHEN vc IS NOT NULL THEN vc { .* } ELSE null END AS constraint
        """
        
        try:
            rows = self.connector.run(query, {"id": device_id})
            matched_rules = []
            for row in rows:
                matched_rules.append({
                    "rule_id": row.get("rule_id"),
                    "predicate": row.get("predicate"),
                    "severity": row.get("severity"),
                    "target_entity": row.get("target_entity"),
                    "constraint": row.get("constraint")
                })
                
            return {
                "device_id": device_id,
                "matched_rules": matched_rules
            }
        except Exception as e:
            logger.error(f"Failed to match rules for device {device_id}: {e}", exc_info=True)
            return {"device_id": device_id, "matched_rules": []}

    def close(self) -> None:
        if self.connector:
            self.connector.close()
