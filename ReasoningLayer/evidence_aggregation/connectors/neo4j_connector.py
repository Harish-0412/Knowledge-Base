"""Neo4j connection management for the inventory knowledge graph."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]


class Neo4jConnector:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        offline: bool = False,
    ) -> None:
        load_dotenv(ROOT / ".env")
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
        self.password = password if password is not None else os.getenv("NEO4J_PASSWORD", "")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self.offline = offline
        self._driver: Optional[Any] = None if offline else self._try_connect()

    def _try_connect(self) -> Optional[Any]:
        if not self.password:
            logger.warning("Neo4j unavailable: NEO4J_PASSWORD is not configured")
            return None
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            driver.verify_connectivity()
            logger.info("Neo4j connected at %s", self.uri)
            return driver
        except Exception as exc:
            logger.warning("Neo4j unavailable (%s); inventory retrieval disabled", exc)
            return None

    @property
    def available(self) -> bool:
        return self._driver is not None

    def run(self, cypher: str, parameters: Optional[Dict] = None) -> List[Dict]:
        if not self.available:
            return []
        try:
            with self._driver.session(database=self.database) as session:
                result = session.run(cypher, parameters or {})
                return [dict(record) for record in result]
        except Exception as exc:
            logger.error("Neo4j query error: %s", exc)
            return []

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None
