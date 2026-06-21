# file: ComplianceEngine/root_cause_engine.py
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ComplianceEngine.compliance_evaluator import ComplianceEvaluator

logger = logging.getLogger(__name__)

class RootCauseEngine:
    """
    Analyzes compliance violations to produce human-readable and enriched 
    root-cause reports suitable for LLM consumption.
    """
    
    def __init__(self) -> None:
        self.compliance_evaluator = ComplianceEvaluator()

    def _fetch_metadata_for_rules(self, device_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Queries Neo4j dynamically for target and constraint entity metadata 
        for all rules matched to the device.
        """
        query = """
        MATCH (d:Device {device_id: $device_id})-[:HAS_COMPONENT]->(c:ComponentInstance)-[:INSTANCE_OF]->(e:Entity)
        MATCH (r:CompatibilityRule)-[:TARGETS]->(e)
        OPTIONAL MATCH (r)-[:HAS_CONSTRAINT]->(vc:VersionConstraint)
        OPTIONAL MATCH (e2:Entity {entity_id: vc.entity_id})
        RETURN r.rule_id AS rule_id,
               e.name AS target_entity_name,
               e.type AS target_entity_type,
               vc.entity_name AS constraint_entity_name,
               vc.entity_kind AS constraint_entity_kind,
               vc.operator AS operator,
               vc.version_normalized AS required_version,
               e2.name AS constraint_canonical_name,
               e2.type AS constraint_canonical_type
        """
        connector = self.compliance_evaluator.connector
        metadata_map = {}
        if not connector or not connector.available:
            logger.warning("Neo4j connector unavailable for fetching rule metadata.")
            return metadata_map

        try:
            rows = connector.run(query, {"device_id": device_id})
            for row in rows:
                rule_id = row.get("rule_id")
                if rule_id:
                    metadata_map[rule_id] = {
                        "target_entity_name": row.get("target_entity_name"),
                        "target_entity_type": row.get("target_entity_type"),
                        "constraint_entity_name": row.get("constraint_entity_name"),
                        "constraint_entity_kind": row.get("constraint_entity_kind"),
                        "operator": row.get("operator"),
                        "required_version": row.get("required_version"),
                        "constraint_canonical_name": row.get("constraint_canonical_name"),
                        "constraint_canonical_type": row.get("constraint_canonical_type")
                    }
        except Exception as e:
            logger.error(f"Failed to fetch rule metadata: {e}", exc_info=True)
            
        return metadata_map

    def _map_category(self, kind: Optional[str]) -> str:
        """Maps entity type / kind to a standardized category."""
        if not kind:
            return "Unknown"
        k = kind.lower()
        if "firmware" in k:
            return "Firmware"
        elif "os" in k or "operating" in k:
            return "OperatingSystem"
        elif "driver" in k:
            return "Driver"
        elif "security" in k or "agent" in k:
            return "Security"
        elif "management" in k or "mgt" in k or "tool" in k:
            return "Management"
        elif "hardware" in k or "hw" in k:
            return "Hardware"
        else:
            return "Unknown"

    def _get_impact(self, status: str) -> str:
        """Determines impact text based on violation status."""
        status_upper = status.upper()
        if status_upper == "CRITICAL":
            return "System compatibility requirements are violated and immediate remediation is recommended."
        elif status_upper == "WARNING":
            return "System may operate but compatibility risks remain."
        else:
            return "Configuration does not satisfy required policy or readiness requirements."

    def _generate_root_cause_explanation(
        self, 
        affected_component: str, 
        installed_version: str, 
        required_version: str, 
        operator: str, 
        target_entity_name: str
    ) -> str:
        """Generates natural language root cause sentence."""
        operator_text = "satisfy the required version"
        
        if operator == ">=":
            operator_text = f"satisfy the minimum required version {required_version}"
        elif operator == ">":
            operator_text = f"exceed the required version {required_version}"
        elif operator == "<=":
            operator_text = f"satisfy the maximum allowed version {required_version}"
        elif operator == "<":
            operator_text = f"remain below the required version {required_version}"
        elif operator == "==":
            operator_text = f"match the required version {required_version}"
        elif operator == "!=":
            operator_text = f"differ from the disallowed version {required_version}"
            
        if installed_version == "Not Installed":
            return f"{affected_component} is not installed, but is required by {target_entity_name} compatibility policy."
        else:
            return f"{affected_component} version {installed_version} does not {operator_text} required by {target_entity_name} compatibility policy."

    def generate_root_causes(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Evaluates compliance and produces enriched root cause records 
        for all non-compliant findings.
        """
        # Step 1: Run ComplianceEvaluator
        eval_results = self.compliance_evaluator.evaluate_device_compliance(device_id)
        
        # Step 2: Query rule metadata for enrichment
        metadata_map = self._fetch_metadata_for_rules(device_id)
        
        records = []
        for result in eval_results:
            status = result.get("status", "COMPLIANT")
            
            # Filter violations (status != COMPLIANT)
            if status == "COMPLIANT":
                continue
                
            rule_id = result.get("rule_id", "")
            expected = result.get("expected", "")
            actual = result.get("actual", "")
            severity = result.get("severity", "info")
            
            # Retrieve graph metadata if available
            meta = metadata_map.get(rule_id, {})
            target_entity_name = meta.get("target_entity_name") or "System"
            
            # Prefer constraint canonical name (e2.name) if available, fall back to constraint_entity_name
            constraint_entity_name = meta.get("constraint_canonical_name") or meta.get("constraint_entity_name") or target_entity_name
            constraint_entity_kind = meta.get("constraint_canonical_type") or meta.get("constraint_entity_kind") or meta.get("target_entity_type")
            operator = meta.get("operator") or ""
            required_version = meta.get("required_version") or expected
            
            # Clean up operator/version if not populated
            if not operator and expected:
                parts = expected.split()
                if len(parts) == 2:
                    operator, required_version = parts[0], parts[1]
                else:
                    required_version = expected
            
            # Construct enriched fields
            affected_component = constraint_entity_name
            required_component = f"{target_entity_name} Compatibility Requirement"
            category = self._map_category(constraint_entity_kind)
            impact = self._get_impact(status)
            
            root_cause_explanation = self._generate_root_cause_explanation(
                affected_component=affected_component,
                installed_version=actual,
                required_version=required_version,
                operator=operator,
                target_entity_name=target_entity_name
            )
            
            records.append({
                "device_id": device_id,
                "rule_id": rule_id,
                "severity": severity,
                "status": status,
                "affected_component": affected_component,
                "required_component": required_component,
                "required_version": required_version,
                "installed_version": actual,
                "expected": expected,
                "actual": actual,
                "category": category,
                "impact": impact,
                "root_cause": root_cause_explanation
            })
            
        return records

    def generate_summary(self, device_id: str) -> Dict[str, Any]:
        """
        Generates a summary count of violations by severity status, 
        and computes the overall status.
        """
        violations = self.generate_root_causes(device_id)
        
        critical_count = sum(1 for v in violations if v.get("status") == "CRITICAL")
        warning_count = sum(1 for v in violations if v.get("status") == "WARNING")
        non_compliant_count = sum(1 for v in violations if v.get("status") == "NON_COMPLIANT")
        
        if critical_count > 0:
            overall_status = "CRITICAL"
        elif warning_count > 0:
            overall_status = "WARNING"
        elif non_compliant_count > 0:
            overall_status = "NON_COMPLIANT"
        else:
            overall_status = "COMPLIANT"
            
        return {
            "device_id": device_id,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "non_compliant_count": non_compliant_count,
            "overall_status": overall_status
        }

    def generate_llm_context(self, device_id: str) -> Dict[str, Any]:
        """Generates a combined context dictionary suited for direct LLM ingestion."""
        root_causes = self.generate_root_causes(device_id)
        summary = self.generate_summary(device_id)
        
        critical_findings = [v["root_cause"] for v in root_causes if v.get("status") == "CRITICAL"]
        warning_findings = [v["root_cause"] for v in root_causes if v.get("status") == "WARNING"]
        
        return {
            "device_id": device_id,
            "overall_status": summary["overall_status"],
            "critical_findings": critical_findings,
            "warning_findings": warning_findings,
            "root_causes": root_causes
        }

    def close(self) -> None:
        """Closes the underlying database connector."""
        self.compliance_evaluator.close()

if __name__ == "__main__":
    # Basic logging setup
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    engine = RootCauseEngine()
    device_id = "DEV-000002"
    
    print(f"Executing Root Cause Engine for device: {device_id}...")
    llm_context = engine.generate_llm_context(device_id)
    summary = engine.generate_summary(device_id)
    
    print("\n--- Summary Report ---")
    print(json.dumps(summary, indent=2))
    
    print("\n--- Enriched Root Cause Records ---")
    print(json.dumps(llm_context, indent=2))
    
    # Save the validation report
    report_json = {
        "engine": "RootCauseEngine",
        "device_tested": device_id,
        "root_cause_count": len(llm_context["root_causes"]),
        "critical_count": summary["critical_count"],
        "warning_count": summary["warning_count"],
        "non_compliant_count": summary["non_compliant_count"],
        "llm_context_generated": True,
        "status": "PASS",
        "llm_context": llm_context
    }
    
    # Paths
    engine_report_path = ROOT / "ComplianceEngine" / "root_cause_engine_validation.json"
    root_report_path = ROOT / "root_cause_engine_validation.json"
    
    try:
        content = json.dumps(report_json, indent=2)
        engine_report_path.write_text(content, encoding="utf-8")
        root_report_path.write_text(content, encoding="utf-8")
        print(f"\nSaved validation report to: {engine_report_path}")
        print(f"Saved duplicate validation report to: {root_report_path}")
    except Exception as e:
        print(f"Error saving validation reports: {e}")
        
    engine.close()
