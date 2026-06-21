"""
Evidence Service — public boundary for the Evidence Aggregation Layer.

Input:  natural-language question (str)  OR  pre-built query plan (dict)
Output: EvidencePackage  /  serialisable dict
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Dict, Optional, Union

try:
    from .evidence_aggregator import EvidenceAggregator
    from .models.evidence_models import EvidencePackage
except ImportError:
    from evidence_aggregator import EvidenceAggregator
    from models.evidence_models import EvidencePackage

# Try to import the Query Understanding Service
try:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
    from ReasoningLayer.query_understanding.query_understanding_service import (
        QueryUnderstandingService,
    )
    _QU_AVAILABLE = True
except ImportError:
    _QU_AVAILABLE = False

logger = logging.getLogger(__name__)


class EvidenceService:
    """
    Single entry-point for the Evidence Aggregation Layer.

    Usage::

        svc = EvidenceService(offline=True)
        pkg = svc.process("Why is Laptop001 non-compliant?")
        print(json.dumps(pkg.to_dict(), indent=2))
    """

    def __init__(self,
                 aggregator: Optional[EvidenceAggregator] = None,
                 offline: bool = False) -> None:
        self.aggregator = aggregator or EvidenceAggregator(offline=offline)
        self._qu: Optional[Any] = (
            QueryUnderstandingService() if _QU_AVAILABLE else None
        )

    def process(self, input: Union[str, Dict[str, Any]]) -> EvidencePackage:
        """
        Accept either a natural-language question or a pre-built query plan.
        Returns an EvidencePackage.
        """
        if isinstance(input, str):
            query_plan = self._understand(input)
        elif isinstance(input, dict):
            query_plan = input
        else:
            raise TypeError(f"input must be str or dict, got {type(input)}")
        return self.aggregator.aggregate(query_plan)

    def _understand(self, question: str) -> Dict[str, Any]:
        if self._qu is not None:
            return self._qu.understand(question)
        # Minimal fallback when Query Understanding is unavailable
        logger.warning("QueryUnderstandingService unavailable — using fallback plan")
        return {
            "question":      question,
            "intent":        "RootCauseAnalysis",
            "confidence":    0.5,
            "intents":       [{"intent": "RootCauseAnalysis", "confidence": 0.5}],
            "intent_mode":   "single",
            "entities":      {},
            "target_layers": ["Layer1", "Layer2", "Layer3"],
            "required_action": "InvestigateViolation",
        }


def aggregate_evidence(question: str, offline: bool = False) -> Dict[str, Any]:
    """Convenience function — returns serialisable dict."""
    return EvidenceService(offline=offline).process(question).to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evidence Aggregation Service — Layer 4 Phase 3")
    parser.add_argument("question", help="Natural-language question")
    parser.add_argument("--offline", action="store_true",
                        help="Run without live Qdrant/Neo4j connections")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG","INFO","WARNING","ERROR"])
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level),
                        format="%(levelname)s %(message)s")
    result = aggregate_evidence(args.question, offline=args.offline)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
