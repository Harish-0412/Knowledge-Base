"""
CompatIQ Retrieval Router
Maps intent → retriever(s) and aggregates results.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.guardrails.retrievers import (
    ComplianceRetriever,
    DocumentChunkRetriever,
    DocumentRetriever,
    ExportRetriever,
    InventoryRetriever,
    KnowledgeBaseRetriever,
    KnowledgeGraphRetriever,
    NormalizedCandidateRetriever,
    RetrievalRequest,
    ReviewStatusRetriever,
    RuleCandidateRetriever,
)
from app.guardrails.schemas import EvidenceItem, RetrievalResult

logger = logging.getLogger(__name__)


def retrieve_for_intent(
    request: "object",                 # GuardedQueryRequest (avoid circular import)
    intent: str,
    capabilities: dict[str, bool],
    db: Session,
) -> RetrievalResult:
    """Route a query to the appropriate retriever(s) based on intent."""

    rr = RetrievalRequest(
        question=request.question,
        intent=intent,
        document_id=request.document_id,
        candidate_id=getattr(request, "candidate_id", None),
        device_id=getattr(request, "device_id", None),
        filters={},
    )

    all_evidence: list[EvidenceItem] = []
    all_unavailable: list[str] = []
    all_warnings: list[str] = []
    all_retrievers: list[str] = []

    def _run(retriever_cls, *args, **kwargs) -> None:
        try:
            result = retriever_cls(*args, **kwargs).retrieve(rr)
            all_evidence.extend(result.evidence)
            all_unavailable.extend(result.unavailable_sources)
            all_warnings.extend(result.warnings)
            all_retrievers.extend(result.retrievers_used)
        except Exception as exc:
            logger.warning("Retriever %s failed: %s", retriever_cls.__name__, exc)

    # ── Intent → retriever mapping ─────────────────────────────────────────

    if intent == "document_summary":
        _run(DocumentRetriever, db)

    elif intent == "document_metadata_lookup":
        _run(DocumentRetriever, db)

    elif intent == "chunk_evidence_lookup":
        _run(DocumentChunkRetriever, db)
        _run(RuleCandidateRetriever, db)

    elif intent == "source_trace":
        _run(DocumentChunkRetriever, db)
        _run(RuleCandidateRetriever, db)

    elif intent in ("rule_candidate_lookup", "normalized_rule_lookup"):
        _run(RuleCandidateRetriever, db)
        _run(NormalizedCandidateRetriever, db)

    elif intent == "review_status_lookup":
        _run(ReviewStatusRetriever, db)

    elif intent == "remediation_from_document":
        _run(RuleCandidateRetriever, db)
        _run(DocumentChunkRetriever, db)

    elif intent in ("unsupported_config_lookup", "known_issue_lookup"):
        _run(RuleCandidateRetriever, db)
        _run(DocumentChunkRetriever, db)

    elif intent == "handoff_status":
        _run(DocumentRetriever, db)
        _run(ExportRetriever, db)

    elif intent == "compatibility_explanation":
        _run(RuleCandidateRetriever, db)
        _run(DocumentChunkRetriever, db)

    elif intent == "general_compatibility_concept":
        pass                            # No retrieval — answer from LLM/template

    elif intent == "capability_question":
        pass                            # No retrieval needed

    elif intent == "requires_kb":
        if capabilities.get("knowledge_base"):
            _run(KnowledgeBaseRetriever)    # Real adapter when connected
        else:
            _run(KnowledgeBaseRetriever)    # Stub returns unavailable

    elif intent == "requires_kg":
        if capabilities.get("knowledge_graph"):
            _run(KnowledgeGraphRetriever)
        else:
            _run(KnowledgeGraphRetriever)   # Stub

    elif intent in ("requires_inventory", "device_compliance_status", "affected_device_query",
                    "rollout_readiness_query"):
        _run(InventoryRetriever)

    elif intent in ("requires_compliance_scan", "violation_explanation"):
        _run(ComplianceRetriever)
        if capabilities.get("knowledge_graph"):
            _run(KnowledgeGraphRetriever)

    elif intent == "root_cause_analysis":
        _run(KnowledgeGraphRetriever)
        _run(ComplianceRetriever)

    elif intent == "fleet_remediation_plan":
        _run(InventoryRetriever)
        _run(ComplianceRetriever)

    elif intent == "out_of_scope":
        pass                            # No retrieval for out-of-scope

    else:
        # Fallback: try candidates + chunks
        _run(RuleCandidateRetriever, db)
        _run(DocumentChunkRetriever, db)

    # Deduplicate evidence by (source_type, source_id)
    seen: set[tuple] = set()
    deduped: list[EvidenceItem] = []
    for ev in all_evidence:
        key = (ev.source_type, ev.source_id)
        if key not in seen:
            seen.add(key)
            deduped.append(ev)

    return RetrievalResult(
        evidence=deduped,
        unavailable_sources=list(dict.fromkeys(all_unavailable)),
        warnings=list(dict.fromkeys(all_warnings)),
        retrievers_used=list(dict.fromkeys(all_retrievers)),
    )
