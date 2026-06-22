"""
CompatIQ Evidence Sufficiency Checker
Evaluates whether the retrieved evidence is adequate to answer the question.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.guardrails.schemas import RetrievalResult


class EvidenceDecision(BaseModel):
    status: str                 # sufficient | partial | missing | capability_missing | unsafe
    reason: str
    limitations: list[str]


def check_evidence(
    intent: str,
    retrieval: RetrievalResult,
    capabilities: dict[str, bool],
    scope_allowed: bool,
) -> EvidenceDecision:
    """Evaluate evidence sufficiency given intent, retrieval results, and capabilities."""
    limitations: list[str] = []

    # ── Unsafe / out-of-scope ────────────────────────────────────────────────
    if not scope_allowed or intent == "out_of_scope":
        return EvidenceDecision(
            status="unsafe",
            reason="Question is out of scope for the CompatIQ assistant.",
            limitations=[],
        )

    # ── General concept — no retrieval needed ─────────────────────────────────
    if intent in ("general_compatibility_concept", "capability_question"):
        return EvidenceDecision(
            status="sufficient",
            reason="General concept question; no specific evidence required.",
            limitations=[],
        )

    # ── Capability-gated intents ──────────────────────────────────────────────
    _CAPABILITY_INTENTS: dict[str, list[str]] = {
        "requires_kg": ["knowledge_graph"],
        "requires_kb": ["knowledge_base"],
        "requires_inventory": ["inventory"],
        "requires_compliance_scan": ["compliance_scan"],
        "device_compliance_status": ["inventory", "compliance_scan"],
        "violation_explanation": ["inventory", "compliance_scan"],
        "root_cause_analysis": ["knowledge_graph"],
        "affected_device_query": ["inventory", "compliance_scan"],
        "rollout_readiness_query": ["inventory", "compliance_scan"],
        "fleet_remediation_plan": ["inventory", "compliance_scan", "remediation_engine"],
        "kg_path_query": ["knowledge_graph"],
        "approved_rule_lookup": ["approved_rules"],
    }
    if intent in _CAPABILITY_INTENTS:
        needed = _CAPABILITY_INTENTS[intent]
        missing_caps = [cap for cap in needed if not capabilities.get(cap)]
        if missing_caps:
            return EvidenceDecision(
                status="capability_missing",
                reason=f"Required capabilities not connected: {', '.join(missing_caps)}",
                limitations=[
                    f"This question requires {cap} which is not connected yet."
                    for cap in missing_caps
                ],
            )

    # ── Check unavailable sources (from stubs) ────────────────────────────────
    if retrieval.unavailable_sources:
        missing_caps = retrieval.unavailable_sources
        return EvidenceDecision(
            status="capability_missing",
            reason=f"Required data sources not available: {', '.join(missing_caps)}",
            limitations=[
                f"{src} is not connected yet. Currently operating in Document Intelligence mode."
                for src in missing_caps
            ],
        )

    # ── No evidence found ─────────────────────────────────────────────────────
    if not retrieval.evidence:
        return EvidenceDecision(
            status="missing",
            reason="No matching evidence found in current CompatIQ data.",
            limitations=[
                "No matching documents, chunks, or rule candidates were found. "
                "Upload or process the relevant document first."
            ],
        )

    # ── Evidence exists — determine quality ───────────────────────────────────
    has_source_page = any(ev.source_page is not None for ev in retrieval.evidence)
    has_source_excerpt = any(ev.source_excerpt for ev in retrieval.evidence)
    all_pending = all(ev.review_status == "pending_review" for ev in retrieval.evidence
                      if ev.review_status is not None)
    has_approved = any(ev.review_status in ("approved", "staged")
                       for ev in retrieval.evidence)

    # Limitation: only pending candidates, no approved rule yet
    if all_pending and not has_approved:
        limitations.append(
            "The matching rule candidates are still pending review and have not been "
            "promoted to an approved rule. Answers are based on candidate evidence only."
        )

    # Limitation: no source page available
    if not has_source_page:
        limitations.append(
            "Source page numbers are not available for all evidence items."
        )

    # Add retrieval warnings as limitations
    limitations.extend(retrieval.warnings)

    # Determine status
    if limitations:
        return EvidenceDecision(
            status="partial",
            reason="Evidence found but with limitations.",
            limitations=limitations,
        )

    return EvidenceDecision(
        status="sufficient",
        reason=f"Retrieved {len(retrieval.evidence)} relevant evidence items.",
        limitations=[],
    )
