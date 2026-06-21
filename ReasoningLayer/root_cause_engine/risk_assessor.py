"""
Risk Assessor — translates a list of detections into final risk levels,
applying scope and confidence modifiers.
"""
from __future__ import annotations
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

RISK_ORDER = ["Informational","Low","Medium","High","Critical"]
RISK_SCORES = {r: i*25 for i, r in enumerate(RISK_ORDER)}

Detection = Tuple[str,str,str,str,float,str]   # (rc_id,viol_id,component,risk,conf,label)


def _boost(risk: str, boost: int = 1) -> str:
    idx = min(RISK_ORDER.index(risk) + boost, len(RISK_ORDER)-1)
    return RISK_ORDER[idx]


class RiskAssessor:
    """Apply modifiers to raw risk levels based on confidence and context."""

    def assess(self, detections: List[Detection],
               device_count: int = 1) -> List[Detection]:
        """
        Modifiers:
        - Low confidence (<0.6) → lower risk by one level.
        - Multiple detections on same component → boost top detection.
        - Fleet scope (device_count > 5) → boost Critical findings.
        """
        if not detections:
            return []

        result = []
        component_counts: dict = {}
        for rc_id, viol_id, component, risk, conf, label in detections:
            component_counts[component] = component_counts.get(component, 0) + 1

        for rc_id, viol_id, component, risk, conf, label in detections:
            adjusted = risk
            # Confidence downgrade
            if conf < 0.6:
                idx = max(RISK_ORDER.index(adjusted) - 1, 0)
                adjusted = RISK_ORDER[idx]
            # Multi-detection boost (same component has > 2 signals)
            if component_counts.get(component, 0) > 2:
                adjusted = _boost(adjusted)
            # Fleet scope boost
            if device_count > 5 and adjusted in ("High","Critical"):
                adjusted = "Critical"
            result.append((rc_id, viol_id, component, adjusted, conf, label))

        logger.debug("RiskAssessor: assessed %d detections", len(result))
        return result
