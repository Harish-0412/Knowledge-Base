"""Execute at least 100 complete query-to-response production tests."""
from __future__ import annotations

import json
from pathlib import Path

from .evaluation_runner import EvaluationRunner


REPORT_PATH = Path(__file__).resolve().parents[1] / "reports" / "end_to_end_validation.json"


def main() -> int:
    result = EvaluationRunner().run(limit=100, write_reports=False)
    report = {
        "test_count": result["metrics"]["total_questions"],
        "metrics": result["metrics"],
        "status": result["status"],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if result["status"] == "READY_FOR_PRODUCTION_DEMO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
