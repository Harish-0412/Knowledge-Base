"""Neo4j connectivity, query, and database statistics."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from .qdrant_connector import _load_root_env


CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "neo4j_config.json"


class Neo4jConnector:
    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        _load_root_env()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")
        self.driver: Any = None

    def connect(self) -> Any:
        if not self.password:
            raise RuntimeError("NEO4J_PASSWORD is not configured")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        self.driver.verify_connectivity()
        return self.driver

    def _driver(self) -> Any:
        return self.driver or self.connect()

    def test_query(self) -> dict[str, Any]:
        records, _, _ = self._driver().execute_query(
            "RETURN 1 AS result", database_=self.database, routing_=None
        )
        return dict(records[0])

    def get_database_stats(self) -> dict[str, int]:
        records, _, _ = self._driver().execute_query(
            "MATCH (n) OPTIONAL MATCH ()-[r]->() RETURN count(DISTINCT n) AS nodes, count(DISTINCT r) AS relationships",
            database_=self.database,
            routing_=None,
        )
        return dict(records[0])

    def health_check(self) -> dict[str, Any]:
        try:
            result = self.test_query()
            return {
                "status": "PASS" if result.get("result") == 1 else "FAIL",
                "reachable": True,
                "database": self.database,
                "test_query": result,
                "error": None,
            }
        except Exception as exc:
            return {
                "status": "FAIL",
                "reachable": False,
                "database": self.database,
                "test_query": None,
                "error": str(exc),
            }

    def close(self) -> None:
        if self.driver is not None:
            self.driver.close()
            self.driver = None

    def __enter__(self) -> "Neo4jConnector":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
