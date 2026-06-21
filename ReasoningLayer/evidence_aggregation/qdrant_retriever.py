"""
Qdrant-based retriever for Layer 1 (domain_knowledge) and
Layer 3 (compatibility_rules) collections.

When Qdrant is offline the retriever returns empty lists and logs a warning.
All public methods are safe to call in offline / unit-test mode.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

try:
    from .connectors.qdrant_connector import QdrantConnector
    from .models.evidence_models import Evidence
except ImportError:
    from connectors.qdrant_connector import QdrantConnector
    from models.evidence_models import Evidence

logger = logging.getLogger(__name__)

DOMAIN_COLLECTION = "kb_domain_layer"
COMPATIBILITY_COLLECTION = "kb_compatibility_layer"
MODEL_NAME = "BAAI/bge-base-en-v1.5"
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class QdrantRetriever:
    """Retrieve domain and compatibility evidence from Qdrant."""

    def __init__(self, connector: Optional[QdrantConnector] = None,
                 offline: bool = False) -> None:
        self.connector = connector or QdrantConnector(offline=offline)
        self.offline   = offline or not self.connector.available
        self._model: Optional[Any] = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def _embed(self, text: str, compatibility: bool = False) -> List[float]:
        if self.offline:
            return []
        value = QUERY_INSTRUCTION + text if compatibility else text
        return self.model.encode(
            value,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()

    # ── domain knowledge ──────────────────────────────────────────────────

    def search_domain(self, query: str, limit: int = 5) -> List[Evidence]:
        """Semantic search over domain_knowledge collection."""
        hits = self.connector.search(
            DOMAIN_COLLECTION, self._embed(query), limit=limit, score_threshold=0.45)
        return [self._to_domain_evidence(h, query) for h in hits]

    def retrieve_by_entity(self, entity_name: str, limit: int = 10) -> List[Evidence]:
        """Retrieve domain records for a named entity."""
        hits = self.connector.scroll(
            DOMAIN_COLLECTION,
            query_filter={"must": [{"key": "name",
                                    "match": {"value": entity_name}}]},
            limit=limit)
        if not hits:
            # Fallback: semantic search on entity name
            hits = self.connector.search(
                DOMAIN_COLLECTION, self._embed(entity_name), limit=limit, score_threshold=0.45)
        return [self._to_domain_evidence(h, entity_name) for h in hits]

    # ── compatibility rules ───────────────────────────────────────────────

    def search_compatibility(self, query: str, limit: int = 10) -> List[Evidence]:
        """Semantic search over compatibility_rules collection."""
        hits = self.connector.search(
            COMPATIBILITY_COLLECTION, self._embed(query, compatibility=True),
            limit=limit, score_threshold=0.45)
        return [self._to_compat_evidence(h, query) for h in hits]

    def retrieve_by_rule(self, rule_id: str) -> List[Evidence]:
        """Retrieve a specific compatibility rule by ID."""
        hits = self.connector.scroll(
            COMPATIBILITY_COLLECTION,
            query_filter={"must": [{"key": "rule_id",
                                    "match": {"value": rule_id}}]},
            limit=1)
        return [self._to_compat_evidence(h, rule_id) for h in hits]

    def retrieve_by_version(self, component: str, version: str) -> List[Evidence]:
        """Retrieve version constraint rules for a component."""
        query = f"{component} version {version}"
        hits  = self.connector.search(
            COMPATIBILITY_COLLECTION, self._embed(query, compatibility=True),
            limit=10, score_threshold=0.45)
        return [self._to_version_evidence(h, component, version) for h in hits]

    # ── builders ──────────────────────────────────────────────────────────

    def _to_domain_evidence(self, hit: Dict, query: str) -> Evidence:
        p = hit.get("payload", {})
        return Evidence(
            evidence_type="DomainEvidence",
            source_layer="Layer1",
            source_system="Qdrant",
            entity=p.get("name") or p.get("entity_name") or p.get("canonical_name") or query,
            confidence=max(0.0, min(1.0, float(hit.get("score", 0.7)))),
            retrieval_score=float(hit.get("score", 0.0)),
            content=p,
            metadata={"collection": DOMAIN_COLLECTION, "doc_id": hit.get("id","")},
        )

    def _to_compat_evidence(self, hit: Dict, query: str) -> Evidence:
        p = hit.get("payload", {})
        return Evidence(
            evidence_type="CompatibilityEvidence",
            source_layer="Layer3",
            source_system="Qdrant",
            entity=p.get("subject") or p.get("subject_entity_name") or p.get("entity") or query,
            relationship=p.get("predicate"),
            target=p.get("object") or p.get("object_entity_name") or p.get("target"),
            confidence=max(0.0, min(1.0, float(p.get("confidence", hit.get("score", 0.8))))),
            retrieval_score=float(hit.get("score", 0.0)),
            content=p,
            metadata={"collection": COMPATIBILITY_COLLECTION, "doc_id": hit.get("id","")},
        )

    def _to_version_evidence(self, hit: Dict, component: str, version: str) -> Evidence:
        p = hit.get("payload", {})
        return Evidence(
            evidence_type="VersionEvidence",
            source_layer="Layer3",
            source_system="Qdrant",
            entity=component,
            target=version,
            confidence=max(0.0, min(1.0, float(p.get("confidence", hit.get("score", 0.8))))),
            retrieval_score=float(hit.get("score", 0.0)),
            content=p,
            metadata={"collection": COMPATIBILITY_COLLECTION, "doc_id": hit.get("id","")},
        )

    # ── connectivity ──────────────────────────────────────────────────────

    def domain_collection_exists(self) -> bool:
        return self.connector.collection_exists(DOMAIN_COLLECTION)

    def compatibility_collection_exists(self) -> bool:
        return self.connector.collection_exists(COMPATIBILITY_COLLECTION)
