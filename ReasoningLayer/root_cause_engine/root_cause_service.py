"""
Root Cause Service — public boundary for the RCA Engine.
Input:  natural-language question (str)  OR  EvidencePackage dict
Output: RCAReport dict
"""
from __future__ import annotations
import argparse, json, logging, sys
from typing import Any, Dict, Optional, Union

try:
    from .root_cause_analyzer    import RootCauseAnalyzer
    from .recommendation_engine  import RecommendationEngine
    from .models.rca_models      import RCAReport
except ImportError:
    from root_cause_analyzer    import RootCauseAnalyzer
    from recommendation_engine  import RecommendationEngine
    from models.rca_models      import RCAReport

# Try Evidence Service
try:
    import sys as _s; from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    from ReasoningLayer.evidence_aggregation.evidence_service import EvidenceService
    _ES_AVAILABLE = True
except ImportError:
    _ES_AVAILABLE = False

logger = logging.getLogger(__name__)


class RootCauseService:
    """End-to-end root cause analysis from question or evidence package."""

    def __init__(self, analyzer: Optional[RootCauseAnalyzer] = None,
                 rec_engine: Optional[RecommendationEngine]  = None,
                 offline: bool = False) -> None:
        self.analyzer   = analyzer   or RootCauseAnalyzer()
        self.rec_engine = rec_engine or RecommendationEngine()
        self._es        = EvidenceService(offline=offline) if _ES_AVAILABLE else None
        self.offline    = offline

    def analyze(self, input: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Accept a question string or pre-built EvidencePackage dict."""
        if isinstance(input, str):
            pkg = self._get_evidence(input)
        elif isinstance(input, dict):
            pkg = input
        else:
            raise TypeError(f"input must be str or dict, got {type(input)}")

        report = self.analyzer.analyze(pkg)
        report_dict = report.to_dict()
        self.rec_engine.enrich(report_dict)
        return report_dict

    def _get_evidence(self, question: str) -> Dict[str, Any]:
        if self._es is not None:
            return self._es.process(question).to_dict()
        logger.warning("EvidenceService unavailable — using minimal plan")
        return {
            "query_id": "QID-FALLBACK",
            "intent":   "RootCauseAnalysis",
            "question": question,
            "entities": [],
            "evidence": [],
            "ranked_evidence": [],
            "evidence_graph":  {},
            "metadata": {},
        }


def analyze_root_cause(question: str, offline: bool = False) -> Dict[str, Any]:
    return RootCauseService(offline=offline).analyze(question)


def main() -> int:
    parser = argparse.ArgumentParser(description="Root Cause Analysis Engine")
    parser.add_argument("question")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG","INFO","WARNING","ERROR"])
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level),
                        format="%(levelname)s %(message)s")
    print(json.dumps(analyze_root_cause(args.question, offline=args.offline), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
