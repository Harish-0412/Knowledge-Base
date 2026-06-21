"""Qdrant connectivity and collection validation."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "qdrant_config.json"


def _load_root_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


class QdrantConnector:
    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        _load_root_env()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.cluster_url = os.getenv("QDRANT_URL", "").strip()
        self.api_key = os.getenv("QDRANT_API_KEY", "").strip()
        self.collections = list(config["collections"])
        self.client: QdrantClient | None = None

    def connect(self) -> QdrantClient:
        if not self.cluster_url:
            raise RuntimeError("QDRANT_URL is not configured")
        self.client = QdrantClient(url=self.cluster_url, api_key=self.api_key or None, timeout=30)
        self.client.get_collections()
        return self.client

    def _client(self) -> QdrantClient:
        return self.client or self.connect()

    def list_collections(self) -> list[str]:
        return [item.name for item in self._client().get_collections().collections]

    def verify_collection(self, name: str) -> bool:
        return name in self.list_collections()

    def verify_domain_collection(self) -> bool:
        return self.verify_collection(self.collections[0])

    def verify_compatibility_collection(self) -> bool:
        return self.verify_collection(self.collections[1])

    def get_collection_stats(self, name: str) -> dict[str, Any]:
        info = self._client().get_collection(name)
        return {
            "name": name,
            "status": str(getattr(info.status, "value", info.status)),
            "points_count": info.points_count,
            "indexed_vectors_count": info.indexed_vectors_count,
        }

    def health_check(self) -> dict[str, Any]:
        try:
            available = self.list_collections()
            missing = [name for name in self.collections if name not in available]
            return {
                "status": "PASS" if not missing else "FAIL",
                "reachable": True,
                "required_collections": self.collections,
                "available_collections": available,
                "missing_collections": missing,
                "error": None if not missing else "Required collections are missing",
            }
        except Exception as exc:
            return {
                "status": "FAIL",
                "reachable": False,
                "required_collections": self.collections,
                "available_collections": [],
                "missing_collections": self.collections,
                "error": str(exc),
            }
