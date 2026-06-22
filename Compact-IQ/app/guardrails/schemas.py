"""
CompatIQ Guardrail Schemas
Pydantic models for the guarded assistant pipeline.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """A single piece of retrieved evidence used to answer a question."""
    source_type: str                            # rule_candidate | chunk | document | ...
    source_id: str | None = None               # candidate_id, chunk_id, etc.
    title: str | None = None
    text: str | None = None                    # Human-readable summary / excerpt
    source_document_id: str | None = None
    source_page: int | None = None
    source_excerpt: str | None = None
    confidence: float | None = None
    review_status: str | None = None
    metadata: dict = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Result from one or more retrievers."""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    unavailable_sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    retrievers_used: list[str] = Field(default_factory=list)


class GuardedQueryRequest(BaseModel):
    """Incoming guarded assistant query."""
    question: str
    document_id: str | None = None
    candidate_id: str | None = None
    device_id: str | None = None
    mode: str = "document_intelligence_only"
    include_guardrail_trace: bool = True


class GuardedQueryResponse(BaseModel):
    """Full structured response from the guarded assistant pipeline."""
    allowed: bool
    intent: str
    mode: str
    answer: str
    evidence_used: list[EvidenceItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggested_next_actions: list[str] = Field(default_factory=list)
    guardrail_trace: dict = Field(default_factory=dict)
