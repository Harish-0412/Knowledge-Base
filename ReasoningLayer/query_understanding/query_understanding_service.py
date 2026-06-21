"""Public service boundary for natural-language query understanding."""

from __future__ import annotations

import argparse
import json

try:
    from .query_parser import QueryParser
except ImportError:
    from query_parser import QueryParser


class QueryUnderstandingService:
    def __init__(self) -> None:
        self.parser = QueryParser()

    def understand(self, question: str) -> dict:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        return self.parser.parse(question.strip())


def understand_query(question: str) -> dict:
    return QueryUnderstandingService().understand(question)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    args = parser.parse_args()
    print(json.dumps(understand_query(args.question), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
