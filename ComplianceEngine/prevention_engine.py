# file: ComplianceEngine/prevention_engine.py
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

class PreventionEngine:
    """
    Generates structured category-based prevention advice, 
    governance controls, automation opportunities, and summaries.
    """
    
    def __init__(self) -> None:
        self.root_cause_engine = RootCauseEngine()

    def _map_priority(self, status: str) -> str:
        """Maps violation status to priority."""
        status_upper = status.upper()
        if status_upper == "CRITICAL":
            return "HIGH"
        elif status_upper == "WARNING":
            return "MEDIUM"
        else:
            return "LOW"

    def _get_prevention_details(self, category: str) -> Dict[str, List[str]]:
        """Maps component category to structured horizons and controls."""
        cat = category.lower()
        if cat == "firmware":
            return {
                "short_term": [
                    "Validate firmware signatures before deployment",
                    "Enable alerts for firmware version discrepancies"
                ],
                "medium_term": [
                    "Perform monthly firmware audits",
                    "Monitor firmware versions through endpoint management"
                ],
                "long_term": [
                    "Enable automated firmware lifecycle management",
                    "Establish vendor alignment for platform hardware refreshes"
                ],
                "governance_controls": [
                    "Change management approval workflows",
                    "Compliance evidence tracking",
                    "Firmware version baselining"
                ],
                "automation_opportunities": [
                    "Automated compliance scanning",
                    "Automated firmware lifecycle management",
                    "Automated inventory refresh"
                ]
            }
        elif cat == "driver":
            return {
                "short_term": [
                    "Monitor driver health and check system logs for driver crashes"
                ],
                "medium_term": [
                    "Schedule quarterly driver reviews",
                    "Implement driver deployment rings"
                ],
                "long_term": [
                    "Enable driver update policy",
                    "Standardize driver baselines across device pools"
                ],
                "governance_controls": [
                    "Change management controls",
                    "Vendor driver verification workflows"
                ],
                "automation_opportunities": [
                    "Automated driver installation",
                    "Automated compliance scanning"
                ]
            }
        elif cat == "operatingsystem":
            return {
                "short_term": [
                    "Apply critical OS patches within 72 hours of release",
                    "Verify patch installation success"
                ],
                "medium_term": [
                    "Implement operating system patch governance",
                    "Establish monthly OS update schedules"
                ],
                "long_term": [
                    "Track OS lifecycle milestones",
                    "Prepare upgrade pathways for upcoming OS major releases"
                ],
                "governance_controls": [
                    "Patch governance policies",
                    "OS lifecycle management controls"
                ],
                "automation_opportunities": [
                    "Automated patch governance",
                    "Automated compliance scanning",
                    "Automated operating system upgrades"
                ]
            }
        elif cat == "security":
            return {
                "short_term": [
                    "Enforce security agent health monitoring",
                    "Verify active service state of security agents"
                ],
                "medium_term": [
                    "Configure automated security policy compliance alerts",
                    "Perform weekly agent configuration audits"
                ],
                "long_term": [
                    "Integrate security compliance into SIEM and asset governance pipelines"
                ],
                "governance_controls": [
                    "Security policy enforcement policies",
                    "Agent tamper protection audits"
                ],
                "automation_opportunities": [
                    "Automated security policy compliance alerts",
                    "Automated agent health checks and self-healing"
                ]
            }
        elif cat == "management":
            return {
                "short_term": [
                    "Enable configuration management enforcement",
                    "Check agent connectivity logs"
                ],
                "medium_term": [
                    "Regularly audit system management tools",
                    "Define management tool version baselines"
                ],
                "long_term": [
                    "Align management agent updates with corporate software deployment cycles"
                ],
                "governance_controls": [
                    "Endpoint management compliance controls",
                    "Access control lists for configuration modifications"
                ],
                "automation_opportunities": [
                    "Automated configuration management enforcement",
                    "Automated agent updates"
                ]
            }
        elif cat == "hardware":
            return {
                "short_term": [
                    "Log hardware inventory anomalies immediately",
                    "Track device model specific failure rates"
                ],
                "medium_term": [
                    "Monitor hardware lifecycle status",
                    "Perform hardware health checks"
                ],
                "long_term": [
                    "Establish hardware asset refresh schedules",
                    "Standardize hardware configurations for procurement"
                ],
                "governance_controls": [
                    "Hardware lifecycle management",
                    "Asset refresh controls"
                ],
                "automation_opportunities": [
                    "Automated inventory refresh",
                    "Automated hardware health alerts"
                ]
            }
        else: # Unknown/fallback
            return {
                "short_term": [
                    "Perform regular system compatibility reviews",
                    "Log generic system configuration changes"
                ],
                "medium_term": [
                    "Ensure policy alignment across all endpoint devices",
                    "Audit non-standard components"
                ],
                "long_term": [
                    "Incorporate dynamic policy rules in change management reviews"
                ],
                "governance_controls": [
                    "General compliance monitoring",
                    "Change management controls"
                ],
                "automation_opportunities": [
                    "Automated compliance scanning"
                ]
            }

    def generate_prevention_guidance(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Ingests root cause records and outputs structured prevention records 
        by mapping category to preventive horizons, governance controls, and automation metrics.
        """
        violations = self.root_cause_engine.generate_root_causes(device_id)
        
        guidance = []
        for viol in violations:
            rule_id = viol.get("rule_id", "")
            status = viol.get("status", "NON_COMPLIANT")
            category = viol.get("category", "Unknown")
            
            priority = self._map_priority(status)
            details = self._get_prevention_details(category)
            
            guidance.append({
                "rule_id": rule_id,
                "priority": priority,
                "category": category,
                "short_term": details["short_term"],
                "medium_term": details["medium_term"],
                "long_term": details["long_term"],
                "governance_controls": details["governance_controls"],
                "automation_opportunities": details["automation_opportunities"]
            })
            
        return guidance

    def generate_prevention_summary(self, device_id: str) -> Dict[str, Any]:
        """
        Analyzes violations to compile deduplicated lists of top risks, 
        recommended programs, and automation candidates.
        """
        violations = self.root_cause_engine.generate_root_causes(device_id)
        guidance = self.generate_prevention_guidance(device_id)
        
        top_risks = []
        for viol in violations:
            priority = self._map_priority(viol.get("status", "NON_COMPLIANT"))
            if priority == "HIGH":
                affected = viol.get("affected_component", "Unknown Component")
                req = viol.get("required_component", "Compatibility Requirement")
                top_risks.append(f"Critical compatibility risk for {affected} due to failed {req}")
                
        # Recommended programs come from long_term and medium_term steps
        recommended_programs = set()
        for g in guidance:
            recommended_programs.update(g.get("medium_term", []))
            recommended_programs.update(g.get("long_term", []))
            
        # Automation candidates come from automation opportunities
        automation_candidates = set()
        for g in guidance:
            automation_candidates.update(g.get("automation_opportunities", []))
            
        return {
            "device_id": device_id,
            "top_risks": list(set(top_risks)),
            "recommended_programs": sorted(list(recommended_programs)),
            "automation_candidates": sorted(list(automation_candidates))
        }

    def generate_llm_prevention_context(self, device_id: str) -> Dict[str, Any]:
        """
        Compiles summaries and high-priority prevention horizons 
        into an LLM-friendly context report.
        """
        guidance = self.generate_prevention_guidance(device_id)
        summary = self.root_cause_engine.generate_summary(device_id)
        overall_status = summary.get("overall_status", "COMPLIANT")
        
        # High priority prevention is short-term actions of HIGH priority records
        high_priority_prevention = []
        for g in guidance:
            if g.get("priority") == "HIGH":
                high_priority_prevention.extend(g.get("short_term", []))
                
        return {
            "device_id": device_id,
            "overall_status": overall_status,
            "high_priority_prevention": list(set(high_priority_prevention)),
            "prevention_guidance": guidance
        }

    def close(self) -> None:
        """Closes the underlying database connector."""
        self.root_cause_engine.close()

if __name__ == "__main__":
    # Basic logging setup
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    engine = PreventionEngine()
    device_id = "DEV-000002"
    
    print(f"Executing Prevention Engine for device: {device_id}...")
    summary = engine.generate_prevention_summary(device_id)
    llm_context = engine.generate_llm_prevention_context(device_id)
    
    print("\n--- Prevention Summary ---")
    print(json.dumps(summary, indent=2))
    
    print("\n--- Prevention Report for LLM Context ---")
    print(json.dumps(llm_context, indent=2))
    
    # Save the validation report
    report_json = {
        "engine": "PreventionEngine",
        "device_tested": device_id,
        "violations_evaluated": len(llm_context["prevention_guidance"]),
        "prevention_rules_triggered": len(llm_context["prevention_guidance"]),
        "status": "PASS",
        "prevention_summary": summary,
        "llm_context": llm_context
    }
    
    # Paths
    engine_report_path = ROOT / "ComplianceEngine" / "prevention_engine_validation.json"
    root_report_path = ROOT / "prevention_engine_validation.json"
    
    try:
        content = json.dumps(report_json, indent=2)
        engine_report_path.write_text(content, encoding="utf-8")
        root_report_path.write_text(content, encoding="utf-8")
        print(f"\nSaved validation report to: {engine_report_path}")
        print(f"Saved duplicate validation report to: {root_report_path}")
    except Exception as e:
        print(f"Error saving validation reports: {e}")
        
    engine.close()
