# file: ComplianceEngine/violation_generator.py
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ComplianceEngine.compliance_evaluator import ComplianceEvaluator

logger = logging.getLogger(__name__)

class ViolationGenerator:
    """Generates Violation records from non-compliant Compliance Evaluation results."""
    
    def __init__(self, evaluator: Optional[ComplianceEvaluator] = None) -> None:
        self.evaluator = evaluator or ComplianceEvaluator()

    def generate_violations_for_device(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Evaluates compliance for a device and generates violation records for any non-compliant statuses.
        """
        eval_results = self.evaluator.evaluate_device_compliance(device_id)
        
        violations = []
        for result in eval_results:
            status = result.get("status")
            if status == "COMPLIANT":
                continue
                
            rule_id = result.get("rule_id", "")
            
            # Generate deterministic violation_id
            violation_id = f"VIOL-{device_id}-{rule_id}"
            
            violations.append({
                "violation_id": violation_id,
                "device_id": device_id,
                "rule_id": rule_id,
                "expected": result.get("expected"),
                "actual": result.get("actual"),
                "severity": result.get("severity"),
                "status": status
            })
            
        return violations

    def close(self) -> None:
        self.evaluator.close()
