"""
CompatIQ Guardrail Retrievers
All retrievers follow the same interface: retrieve(request) -> RetrievalResult.

Current retrievers use existing SQLAlchemy repositories.
Future retrievers (KB, KG, Inventory, Compliance) are stubbed out.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.guardrails.schemas import EvidenceItem, RetrievalResult
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.rule_candidate_repository import RuleCandidateRepository

logger = logging.getLogger(__name__)

# ── Request dataclass (avoids circular import with schemas) ───────────────────

@dataclass
class RetrievalRequest:
    question: str
    intent: str
    document_id: str | None = None
    candidate_id: str | None = None
    device_id: str | None = None
    filters: dict | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text_matches(text: str | None, q: str) -> bool:
    """Case-insensitive substring match — used when semantic search unavailable."""
    if not text:
        return False
    return q.lower() in text.lower()


def _score_candidate_match(candidate, q_lower: str) -> bool:
    """Return True if this rule candidate is relevant to the question."""
    # Match on rule_id
    if candidate.rule_id and candidate.rule_id.lower() in q_lower:
        return True
    # Match on any COMP-/UNSUP-/REC- token in question
    import re
    id_tokens = re.findall(r"(?:comp|unsup|rec|rcand)-\d+", q_lower, re.I)
    if candidate.rule_id and any(t in candidate.rule_id.lower() for t in id_tokens):
        return True
    # Match on source excerpt text
    if candidate.source_excerpt and _text_matches(candidate.source_excerpt, q_lower):
        return True
    # Match on component keywords in normalized rule JSON
    if candidate.normalized_rule_json:
        nrj = str(candidate.normalized_rule_json).lower()
        for kw in ["bios", "tpm", "firmware", "nic", "nvidia", "crowdstrike",
                   "intune", "secure boot", "driver", "os", "windows"]:
            if kw in q_lower and kw in nrj:
                return True
    # Match on explanation text
    if candidate.explanation and _text_matches(candidate.explanation, q_lower):
        return True
    return False


def _candidate_to_evidence(candidate) -> EvidenceItem:
    meta = dict(candidate.metadata_json or {})
    return EvidenceItem(
        source_type="rule_candidate",
        source_id=str(candidate.candidate_id),
        title=candidate.rule_id or f"Candidate #{candidate.candidate_id}",
        text=candidate.explanation or candidate.source_excerpt or "",
        source_document_id=candidate.document_id,
        source_page=None,               # page not stored on candidate directly
        source_excerpt=candidate.source_excerpt or None,
        confidence=candidate.confidence_score,
        review_status=candidate.review_status,
        metadata={
            "rule_type": candidate.rule_type,
            "severity": candidate.severity,
            "normalization_status": candidate.normalization_status,
            "confidence_reason": candidate.confidence_reason,
            "tier": meta.get("review_tier"),
            "auto_approved": meta.get("auto_approved"),
        },
    )


def _chunk_to_evidence(chunk) -> EvidenceItem:
    return EvidenceItem(
        source_type="document_chunk",
        source_id=str(chunk.chunk_id),
        title=chunk.section_title or chunk.chunk_type,
        text=chunk.text[:500] if chunk.text else "",
        source_document_id=chunk.document_id,
        source_page=chunk.page_number,
        source_excerpt=chunk.source_excerpt[:400] if chunk.source_excerpt else None,
        confidence=chunk.quality_score,
        review_status=None,
        metadata={
            "chunk_type": chunk.chunk_type,
            "rule_likelihood": chunk.rule_likelihood,
            "semantic_zone": chunk.semantic_zone,
        },
    )


# ── Current Retrievers ────────────────────────────────────────────────────────

class DocumentRetriever:
    """Retrieve metadata for one or all documents."""

    def __init__(self, db: Session) -> None:
        self._repo = DocumentRepository(db)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        evidence: list[EvidenceItem] = []
        try:
            if request.document_id:
                doc = self._repo.get_by_id(request.document_id)
                if doc:
                    evidence.append(EvidenceItem(
                        source_type="document",
                        source_id=doc.document_id,
                        title=doc.original_filename or doc.filename,
                        text=f"Document '{doc.original_filename}' — status: {doc.status}",
                        source_document_id=doc.document_id,
                        metadata={
                            "status": doc.status,
                            "source_type": doc.source_type,
                            "file_size_bytes": doc.file_size_bytes,
                            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                        },
                    ))
            else:
                docs = self._repo.list_all()
                for doc in docs[:10]:
                    evidence.append(EvidenceItem(
                        source_type="document",
                        source_id=doc.document_id,
                        title=doc.original_filename or doc.filename,
                        text=f"Document '{doc.original_filename}' — status: {doc.status}",
                        source_document_id=doc.document_id,
                        metadata={"status": doc.status},
                    ))
        except Exception as exc:
            logger.warning("DocumentRetriever error: %s", exc)
        return RetrievalResult(evidence=evidence, retrievers_used=["document"])


class DocumentChunkRetriever:
    """Retrieve document chunks matching the question keywords."""

    def __init__(self, db: Session) -> None:
        self._repo = ChunkRepository(db)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        evidence: list[EvidenceItem] = []
        try:
            q = request.question.lower()
            if request.document_id:
                chunks = self._repo.list_chunks_for_document(request.document_id)
            else:
                # Without document context we can't enumerate all chunks easily;
                # return empty and let the candidate retriever cover cross-doc search.
                return RetrievalResult(
                    evidence=[],
                    warnings=["No document_id provided; chunk search requires a document context."],
                    retrievers_used=["document_chunk"],
                )

            matched = [c for c in chunks if _text_matches(c.text, q)
                       or _text_matches(c.source_excerpt, q)
                       or _text_matches(c.section_title, q)]
            for chunk in matched[:8]:
                evidence.append(_chunk_to_evidence(chunk))
        except Exception as exc:
            logger.warning("DocumentChunkRetriever error: %s", exc)
        return RetrievalResult(evidence=evidence, retrievers_used=["document_chunk"])


class RuleCandidateRetriever:
    """Retrieve rule candidates matching the question."""

    def __init__(self, db: Session) -> None:
        self._repo = RuleCandidateRepository(db)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        evidence: list[EvidenceItem] = []
        try:
            q = request.question.lower()
            if request.document_id:
                candidates = self._repo.list_by_document(request.document_id)
            else:
                candidates = self._repo.list_all()

            for candidate in candidates:
                if _score_candidate_match(candidate, q):
                    evidence.append(_candidate_to_evidence(candidate))
                    if len(evidence) >= 10:
                        break
        except Exception as exc:
            logger.warning("RuleCandidateRetriever error: %s", exc)
        return RetrievalResult(evidence=evidence, retrievers_used=["rule_candidate"])


class NormalizedCandidateRetriever:
    """Retrieve normalized rule candidates (those that have been normalized)."""

    def __init__(self, db: Session) -> None:
        self._repo = RuleCandidateRepository(db)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        evidence: list[EvidenceItem] = []
        try:
            q = request.question.lower()
            if request.document_id:
                candidates = self._repo.list_by_document(request.document_id)
            else:
                candidates = self._repo.list_all()

            for c in candidates:
                if c.normalization_status != "normalized":
                    continue
                if _score_candidate_match(c, q):
                    ev = _candidate_to_evidence(c)
                    if c.normalized_rule_json:
                        ev.metadata["normalized_rule"] = c.normalized_rule_json
                    evidence.append(ev)
                    if len(evidence) >= 10:
                        break
        except Exception as exc:
            logger.warning("NormalizedCandidateRetriever error: %s", exc)
        return RetrievalResult(evidence=evidence, retrievers_used=["normalized_candidate"])


class ReviewStatusRetriever:
    """Retrieve candidates grouped by review status."""

    def __init__(self, db: Session) -> None:
        self._repo = RuleCandidateRepository(db)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        evidence: list[EvidenceItem] = []
        try:
            if request.document_id:
                candidates = self._repo.list_by_document(request.document_id)
            else:
                candidates = self._repo.list_all()

            # Determine which status is being asked about
            q = request.question.lower()
            status_filter: str | None = None
            for status in ["pending_review", "approved", "rejected",
                           "needs_clarification", "staged"]:
                if status.replace("_", " ") in q or status in q:
                    status_filter = status
                    break
            if "pending" in q:
                status_filter = "pending_review"

            for c in candidates:
                if status_filter and c.review_status != status_filter:
                    continue
                evidence.append(_candidate_to_evidence(c))
                if len(evidence) >= 15:
                    break
        except Exception as exc:
            logger.warning("ReviewStatusRetriever error: %s", exc)
        return RetrievalResult(evidence=evidence, retrievers_used=["review_status"])


class ExportRetriever:
    """Placeholder — returns document export metadata when document_id given."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        if not request.document_id:
            return RetrievalResult(
                evidence=[],
                warnings=["Export retriever requires a document_id."],
                retrievers_used=["export"],
            )
        return RetrievalResult(
            evidence=[EvidenceItem(
                source_type="export",
                source_id=request.document_id,
                title=f"Exports for {request.document_id}",
                text=f"Local exports available under storage/exports/{request.document_id}/",
                source_document_id=request.document_id,
                metadata={"export_path": f"storage/exports/{request.document_id}/"},
            )],
            retrievers_used=["export"],
        )


# ── Future Stub Retrievers ────────────────────────────────────────────────────

class KnowledgeBaseRetriever:
    """STUB — Knowledge Base semantic retrieval (pgvector/approved rules).
    Plug in real implementation when KB is connected.
    """

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        return RetrievalResult(
            evidence=[],
            unavailable_sources=["knowledge_base"],
            warnings=["Knowledge Base retriever is not connected yet. "
                      "Set GUARDRAILS_KB_ENABLED=true when KB is ready."],
            retrievers_used=["knowledge_base"],
        )


class KnowledgeGraphRetriever:
    """STUB — Knowledge Graph traversal (Neo4j / graph paths).
    Plug in real implementation when KG is connected.
    """

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        return RetrievalResult(
            evidence=[],
            unavailable_sources=["knowledge_graph"],
            warnings=["Knowledge Graph retriever is not connected yet. "
                      "Set GUARDRAILS_KG_ENABLED=true when KG is ready."],
            retrievers_used=["knowledge_graph"],
        )


class InventoryRetriever:
    """STUB — Device inventory retrieval.
    Plug in real implementation when inventory is connected.
    """

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        return RetrievalResult(
            evidence=[],
            unavailable_sources=["inventory"],
            warnings=["Inventory retriever is not connected yet. "
                      "Set GUARDRAILS_INVENTORY_ENABLED=true when inventory is ready."],
            retrievers_used=["inventory"],
        )


class ComplianceRetriever:
    """STUB — Compliance scan result retrieval.
    Plug in real implementation when compliance scan is connected.
    """

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        return RetrievalResult(
            evidence=[],
            unavailable_sources=["compliance_scan"],
            warnings=["Compliance scan retriever is not connected yet. "
                      "Set GUARDRAILS_COMPLIANCE_ENABLED=true when compliance is ready."],
            retrievers_used=["compliance"],
        )
