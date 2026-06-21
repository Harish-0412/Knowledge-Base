# file: ComplianceEngine/compliance_evaluator.py
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ComplianceEngine.rule_matcher import RuleMatcher
from ComplianceEngine.version_comparator import compare_versions

logger = logging.getLogger(__name__)

class ComplianceEvaluator:
    """Evaluates device compliance against matched compatibility rules and version constraints."""
    
    def __init__(self, matcher: Optional[RuleMatcher] = None) -> None:
        self.matcher = matcher or RuleMatcher()
        self.connector = self.matcher.connector

    def get_installed_versions(self, device_id: str) -> Dict[str, str]:
        """Retrieves installed versions of all components on the given device."""
        query = """
        MATCH (d:Device {device_id: $id})-[:HAS_COMPONENT]->(c:ComponentInstance)-[:INSTANCE_OF]->(e:Entity)
        RETURN e.entity_id AS entity_id,
               c.version_normalized AS version_normalized,
               c.version_raw AS version_raw
        """
        
        installed = {}
        try:
            rows = self.connector.run(query, {"id": device_id})
            for row in rows:
                entity_id = row.get("entity_id")
                version = row.get("version_normalized") or row.get("version_raw") or "0.0.0"
                if entity_id:
                    installed[entity_id] = version
        except Exception as e:
            logger.error(f"Failed to query installed versions for device {device_id}: {e}", exc_info=True)
            
        return installed

    def evaluate_device_compliance(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Evaluates the compliance of a device against all applicable compatibility rules.
        """
        # 1. Match all rules for this device
        match_result = self.matcher.match_rules_for_device(device_id)
        matched_rules = match_result.get("matched_rules", [])
        
        # 2. Get installed component versions
        installed_versions = self.get_installed_versions(device_id)
        
        evaluation_results = []
        for rule in matched_rules:
            rule_id = rule.get("rule_id")
            severity = rule.get("severity") or "info"
            constraint = rule.get("constraint")
            
            if not constraint:
                # If no constraint exists, treat as compliant by default
                evaluation_results.append({
                    "rule_id": rule_id,
                    "device_id": device_id,
                    "expected": "None",
                    "actual": "None",
                    "severity": severity,
                    "status": "COMPLIANT"
                })
                continue
                
            req_entity_id = constraint.get("entity_id")
            operator = constraint.get("operator") or "=="
            req_version = constraint.get("version_normalized") or constraint.get("version_raw") or ""
            
            # Format expected string, e.g. ">= 8.2.0"
            expected_str = f"{operator} {req_version}".strip()
            
            # Check if component is installed
            installed_version = installed_versions.get(req_entity_id)
            
            if installed_version is None:
                actual_str = "Not Installed"
                is_compliant = False
            else:
                actual_str = installed_version
                try:
                    is_compliant = compare_versions(installed_version, operator, req_version)
                except Exception as e:
                    logger.warning(f"Version comparison failed for rule {rule_id}: {e}")
                    is_compliant = False
                    
            if is_compliant:
                status = "COMPLIANT"
            else:
                if severity == "critical":
                    status = "CRITICAL"
                elif severity == "warning":
                    status = "WARNING"
                else:
                    status = "NON_COMPLIANT"
                    
            evaluation_results.append({
                "rule_id": rule_id,
                "device_id": device_id,
                "expected": expected_str,
                "actual": actual_str,
                "severity": severity,
                "status": status
            })
            
        return evaluation_results

    def close(self) -> None:
        self.matcher.close()
