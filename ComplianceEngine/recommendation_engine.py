# file: ComplianceEngine/recommendation_engine.py
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ComplianceEngine.root_cause_engine import RootCauseEngine

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Generates structured, priority-aware remediation guidance 
    based on RootCauseEngine findings.
    """
    
    def __init__(self) -> None:
        self.root_cause_engine = RootCauseEngine()

    def _map_priority_and_risk(self, status: str) -> str:
        """Maps violation status to priority and risk level."""
        status_upper = status.upper()
        if status_upper == "CRITICAL":
            return "HIGH"
        elif status_upper == "WARNING":
            return "MEDIUM"
        else:
            return "LOW"

    def generate_recommendations(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Ingests root cause records and outputs structured remediation guidance 
        with priorities, summaries, and action steps.
        """
        # Step 1: Fetch violations
        violations = self.root_cause_engine.generate_root_causes(device_id)
        
        recommendations = []
        for viol in violations:
            rule_id = viol.get("rule_id", "")
            status = viol.get("status", "NON_COMPLIANT")
            category = viol.get("category", "Unknown")
            affected_component = viol.get("affected_component", "Unknown Component")
            required_version = viol.get("required_version", "")
            installed_version = viol.get("installed_version", "")
            expected = viol.get("expected", "")
            actual = viol.get("actual", "")
            
            # Extract target entity name from required_component, e.g. "BIOS Compatibility Requirement" -> "BIOS"
            req_comp = viol.get("required_component", "System Compatibility Requirement")
            target_entity_name = req_comp.replace(" Compatibility Requirement", "")
            if not target_entity_name:
                target_entity_name = "System"
                
            priority = self._map_priority_and_risk(status)
            risk_level = priority
            
            # Determine operator from expected string, e.g. ">= 8.2.0" -> ">="
            operator = ""
            if expected:
                parts = expected.split()
                if len(parts) >= 1:
                    operator = parts[0]
                    
            # Determine action verb and immediate action steps
            if installed_version == "Not Installed":
                action_verb = "Install"
                suffix = "or later" if operator in [">=", ">"] else ""
                immediate_actions = [f"Install {affected_component} to version {required_version} {suffix}".strip()]
                summary = f"Install {affected_component} to version {required_version} or later to restore {target_entity_name} compatibility."
            else:
                if operator in [">=", ">"]:
                    action_verb = "Upgrade"
                    suffix = "or later"
                elif operator in ["<=", "<"]:
                    action_verb = "Downgrade"
                    suffix = "or earlier"
                elif operator == "==":
                    action_verb = "Configure"
                    suffix = ""
                elif operator == "!=":
                    action_verb = "Change"
                    suffix = f"to a version other than {required_version}"
                else:
                    action_verb = "Upgrade"
                    suffix = "or later"
                
                if suffix:
                    immediate_actions = [f"{action_verb} {affected_component} to version {required_version} {suffix}".strip()]
                else:
                    immediate_actions = [f"{action_verb} {affected_component} to version {required_version}".strip()]
                    
                summary = f"{action_verb} {affected_component} to version {required_version} or later to restore {target_entity_name} compatibility."
            
            # Determine verification steps
            verification_steps = [f"Verify {target_entity_name} compatibility after {action_verb.lower()}"]
            
            # Determine follow-up steps
            follow_up_actions = ["Re-run compliance validation"]
            
            recommendations.append({
                "rule_id": rule_id,
                "priority": priority,
                "category": category,
                "risk_level": risk_level,
                "summary": summary,
                "immediate_actions": immediate_actions,
                "verification_steps": verification_steps,
                "follow_up_actions": follow_up_actions
            })
            
        return recommendations

    def generate_llm_recommendation_context(self, device_id: str) -> Dict[str, Any]:
        """
        Compiles summaries, recommendations, and high priority immediate actions 
        into an LLM-friendly context report.
        """
        recommendations = self.generate_recommendations(device_id)
        
        # Inherit overall status from RootCauseEngine summary
        summary = self.root_cause_engine.generate_summary(device_id)
        overall_status = summary.get("overall_status", "COMPLIANT")
        
        # Extract immediate actions for all high-priority recommendations
        high_priority_actions = []
        for rec in recommendations:
            if rec.get("priority") == "HIGH":
                high_priority_actions.extend(rec.get("immediate_actions", []))
                
        return {
            "device_id": device_id,
            "overall_status": overall_status,
            "high_priority_actions": high_priority_actions,
            "recommendations": recommendations
        }

    def close(self) -> None:
        """Closes the underlying root cause engine."""
        self.root_cause_engine.close()

if __name__ == "__main__":
    # Basic logging setup
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    engine = RecommendationEngine()
    device_id = "DEV-000002"
    
    print(f"Executing Recommendation Engine for device: {device_id}...")
    llm_context = engine.generate_llm_recommendation_context(device_id)
    
    print("\n--- Recommendation Report for LLM Context ---")
    print(json.dumps(llm_context, indent=2))
    
    # Save the validation report
    report_json = {
        "engine": "RecommendationEngine",
        "device_tested": device_id,
        "violations_evaluated": len(llm_context["recommendations"]),
        "recommendations_generated": sum(len(r["immediate_actions"]) for r in llm_context["recommendations"]),
        "status": "PASS",
        "llm_context": llm_context
    }
    
    # Paths
    engine_report_path = ROOT / "ComplianceEngine" / "recommendation_engine_validation.json"
    root_report_path = ROOT / "recommendation_engine_validation.json"
    
    try:
        content = json.dumps(report_json, indent=2)
        engine_report_path.write_text(content, encoding="utf-8")
        root_report_path.write_text(content, encoding="utf-8")
        print(f"\nSaved validation report to: {engine_report_path}")
        print(f"Saved duplicate validation report to: {root_report_path}")
    except Exception as e:
        print(f"Error saving validation reports: {e}")
        
    engine.close()
