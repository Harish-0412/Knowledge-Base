"""Qdrant connection management for the live knowledge collections."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]


class QdrantConnector:
    """Thin Qdrant wrapper with an explicit offline mode for unit tests."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        offline: bool = False,
        url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        load_dotenv(ROOT / ".env")
        self.host = host
        self.port = port
        self.url = (url or os.getenv("QDRANT_URL", "")).strip()
        self.api_key = (api_key or os.getenv("QDRANT_API_KEY", "")).strip()
        self.offline = offline
        self._client: Optional[Any] = None if offline else self._try_connect()

    def _try_connect(self) -> Optional[Any]:
        try:
            from qdrant_client import QdrantClient

            if self.url:
                client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key or None,
                    timeout=60,
                    check_compatibility=False,
                )
            else:
                client = QdrantClient(host=self.host, port=self.port, timeout=30)
            client.get_collections()
            logger.info("Qdrant connected at %s", self.url or f"{self.host}:{self.port}")
            return client
        except Exception as exc:
            logger.warning("Qdrant unavailable (%s); retrieval disabled", exc)
            return None

    @property
    def available(self) -> bool:
        return self._client is not None

    def search(
        self,
        collection: str,
        vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        query_filter: Optional[Dict] = None,
    ) -> List[Dict]:
        if not self.available:
            return []
        try:
            response = self._client.query_points(
                collection_name=collection,
                query=vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=False,
            )
            return [
                {"id": str(point.id), "score": float(point.score), "payload": point.payload or {}}
                for point in response.points
            ]
        except Exception as exc:
            logger.error("Qdrant search error for %s: %s", collection, exc)
            return []

    def scroll(
        self,
        collection: str,
        query_filter: Optional[Dict] = None,
        limit: int = 20,
    ) -> List[Dict]:
        if not self.available:
            return []
        try:
            records, _ = self._client.scroll(
                collection_name=collection,
                scroll_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            return [
                {"id": str(record.id), "score": 1.0, "payload": record.payload or {}}
                for record in records
            ]
        except Exception as exc:
            logger.error("Qdrant scroll error for %s: %s", collection, exc)
            return []

    def collection_exists(self, collection: str) -> bool:
        if not self.available:
            return False
        try:
            return bool(self._client.collection_exists(collection))
        except Exception:
            return False
