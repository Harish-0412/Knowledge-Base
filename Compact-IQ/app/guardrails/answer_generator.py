"""
CompatIQ Answer Generator
Generates answers from evidence — either deterministic templates or grounded LLM.

Deterministic mode (default): always works, no LLM required. Tests pass without Ollama.
LLM mode (opt-in via GUARDRAILS_USE_LLM_ANSWER=true): uses existing LLM service.
"""
from __future__ import annotations

import logging
import os

from app.guardrails.evidence_checker import EvidenceDecision
from app.guardrails.response_templates import (
    capability_missing_response,
    capability_question_response,
    general_concept_response,
    insufficient_evidence_response,
    out_of_scope_response,
    partial_evidence_prefix,
    prompt_injection_response,
)
from app.guardrails.schemas import EvidenceItem, RetrievalResult

logger = logging.getLogger(__name__)

_USE_LLM = os.environ.get("GUARDRAILS_USE_LLM_ANSWER", "false").strip().lower() in ("true", "1")


def _summarize_evidence(
    evidence: list[EvidenceItem],
    intent: str,
    question: str,
) -> str:
    """Build a deterministic answer from retrieved evidence items."""
    if not evidence:
        return insufficient_evidence_response(intent)

    lines: list[str] = []
    q = question.lower()

    # Intent-specific summarization
    if intent == "review_status_lookup":
        from collections import Counter
        statuses = Counter(ev.review_status for ev in evidence if ev.review_status)
        total = len(evidence)
        lines.append(f"Found **{total} rule candidate(s)** matching your query.\n")
        if statuses:
            lines.append("**Review Status Breakdown:**")
            for status, count in statuses.most_common():
                lines.append(f"- {status}: {count} candidate(s)")
            lines.append("")
        for ev in evidence[:6]:
            rule_id = ev.title or ev.source_id
            status = ev.review_status or "unknown"
            doc = ev.source_document_id or "unknown doc"
            lines.append(f"- **{rule_id}** — status: `{status}` (doc: {doc})")
        return "\n".join(lines)

    elif intent in ("normalized_rule_lookup", "rule_candidate_lookup"):
        for ev in evidence[:5]:
            rule_id = ev.title or ev.source_id or "Unknown"
            lines.append(f"**{rule_id}**")
            if ev.review_status:
                lines.append(f"Review Status: `{ev.review_status}`")
            if ev.confidence is not None:
                lines.append(f"Confidence: {ev.confidence:.0%}")
            if ev.source_excerpt:
                lines.append(f'Source Excerpt: *"{ev.source_excerpt[:300]}"*')
            if ev.source_document_id:
                lines.append(f"Source Document: {ev.source_document_id}")
            if ev.source_page:
                lines.append(f"Source Page: {ev.source_page}")
            meta = ev.metadata
            if meta.get("rule_type"):
                lines.append(f"Rule Type: {meta['rule_type']}")
            if meta.get("severity"):
                lines.append(f"Severity: {meta['severity']}")
            if meta.get("normalization_status") == "normalized" and meta.get("normalized_rule"):
                lines.append(f"Normalized Rule: `{str(meta['normalized_rule'])[:200]}`")
            if ev.review_status == "pending_review":
                lines.append(
                    "> ⚠️ This is a **pending review candidate**, not an approved rule. "
                    "It has not been promoted to the approved rule repository."
                )
            lines.append("")
        return "\n".join(lines).strip()

    elif intent == "chunk_evidence_lookup":
        lines.append(f"Found **{len(evidence)} evidence item(s)** matching your query:\n")
        for ev in evidence[:6]:
            if ev.source_type == "document_chunk":
                lines.append(f"**Page {ev.source_page or '?'} — {ev.title or 'Chunk'}**")
                if ev.source_excerpt:
                    lines.append(f'> "{ev.source_excerpt[:350]}"')
                lines.append(f"Document: {ev.source_document_id or 'unknown'}")
                if ev.metadata.get("rule_likelihood"):
                    lines.append(f"Rule Likelihood: {ev.metadata['rule_likelihood']}")
            elif ev.source_type == "rule_candidate":
                lines.append(f"**Rule Candidate {ev.title}** (`{ev.review_status}`)")
                if ev.source_excerpt:
                    lines.append(f'> "{ev.source_excerpt[:350]}"')
            lines.append("")
        return "\n".join(lines).strip()

    elif intent == "remediation_from_document":
        remed_evidence = [ev for ev in evidence if ev.source_excerpt and any(
            kw in (ev.source_excerpt or "").lower()
            for kw in ["remediat", "upgrade", "required action", "workaround",
                       "recommendation", "must", "should", "install"]
        )]
        if remed_evidence:
            lines.append("**Remediation guidance found in document evidence:**\n")
            for ev in remed_evidence[:5]:
                lines.append(f"- *{ev.source_excerpt[:300]}*")
                if ev.source_document_id:
                    lines.append(f"  _(Source: {ev.source_document_id}"
                                 + (f", Page {ev.source_page}" if ev.source_page else "") + ")_")
                lines.append("")
            lines.append(
                "> ⚠️ These steps are based on document evidence only. "
                "Approved remediation plans require human review and final rule promotion."
            )
        else:
            lines.append(
                "I found related document evidence, but no explicit remediation guidance "
                "was identified in the extracted chunks or rule candidates for this query. "
                "Please review the source document directly."
            )
        return "\n".join(lines).strip()

    elif intent == "unsupported_config_lookup":
        unsup = [ev for ev in evidence if ev.title and (
            "unsup" in (ev.title or "").lower() or
            "unsupported" in (ev.source_excerpt or "").lower()
        )]
        if not unsup:
            unsup = evidence
        lines.append(f"Found **{len(unsup)} unsupported configuration candidate(s)**:\n")
        for ev in unsup[:6]:
            lines.append(f"- **{ev.title or ev.source_id}** (`{ev.review_status}`)")
            if ev.source_excerpt:
                lines.append(f'  > "{ev.source_excerpt[:250]}"')
        return "\n".join(lines).strip()

    elif intent == "document_summary":
        lines.append(f"Found **{len(evidence)} document(s)**:\n")
        for ev in evidence[:5]:
            lines.append(f"- **{ev.title}** (ID: {ev.source_id}, Status: {ev.metadata.get('status', '?')})")
        return "\n".join(lines).strip()

    elif intent == "source_trace":
        lines.append("**Source evidence trace:**\n")
        for ev in evidence[:5]:
            doc = ev.source_document_id or "unknown"
            page = f", Page {ev.source_page}" if ev.source_page else ""
            lines.append(f"- {ev.source_type.replace('_', ' ').title()} **{ev.title or ev.source_id}**")
            lines.append(f"  Source: {doc}{page}")
            if ev.source_excerpt:
                lines.append(f'  > "{ev.source_excerpt[:300]}"')
            lines.append("")
        return "\n".join(lines).strip()

    # Generic fallback: list all evidence
    lines.append(f"Found **{len(evidence)} relevant item(s)** based on Document Intelligence data:\n")
    for ev in evidence[:8]:
        title = ev.title or ev.source_id or "Item"
        lines.append(f"- **{title}** ({ev.source_type})")
        if ev.source_excerpt:
            lines.append(f'  *"{ev.source_excerpt[:200]}"*')
        if ev.review_status:
            lines.append(f"  Status: `{ev.review_status}`")
        if ev.source_document_id:
            lines.append(f"  Document: {ev.source_document_id}")
    lines.append(
        "\n_This answer is based on Document Intelligence evidence. "
        "For final approved rules, KB/KG modules must be connected._"
    )
    return "\n".join(lines).strip()


def _try_llm_answer(
    system_prompt: str,
    user_prompt: str,
) -> str | None:
    """Attempt to generate a grounded LLM answer. Returns None on failure."""
    try:
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()
        combined = f"{system_prompt}\n\n{user_prompt}"
        result = llm.generate_text(combined)
        if isinstance(result, str) and result.strip():
            return result.strip()
    except Exception as exc:
        logger.warning("LLM answer generation failed: %s", exc)
    return None


def generate_answer(
    question: str,
    intent: str,
    evidence_decision: EvidenceDecision,
    retrieval: RetrievalResult,
    capabilities: dict[str, bool],
    scope_allowed: bool,
    is_injection: bool = False,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
) -> tuple[str, str]:
    """Generate the final answer string and response mode.

    Returns (answer_text, response_mode).
    """
    # ── Blocked responses ────────────────────────────────────────────────────
    if is_injection:
        return prompt_injection_response(), "blocked_unsafe"

    if not scope_allowed or intent == "out_of_scope":
        return out_of_scope_response(), "blocked_out_of_scope"

    # ── Special intent responses ─────────────────────────────────────────────
    if intent == "capability_question":
        return capability_question_response(), "answered_general_concept"

    if intent == "general_compatibility_concept":
        return general_concept_response(question), "answered_general_concept"

    # ── Evidence-gated responses ─────────────────────────────────────────────
    ev_status = evidence_decision.status

    if ev_status == "capability_missing":
        missing = [cap for cap in ["knowledge_graph", "knowledge_base", "inventory",
                                   "compliance_scan", "remediation_engine", "approved_rules"]
                   if not capabilities.get(cap) and cap in " ".join(evidence_decision.limitations)]
        # If limitations don't mention specific caps, derive from intent
        if not missing:
            from app.guardrails.capabilities import INTENT_REQUIRED_CAPABILITIES
            needed = INTENT_REQUIRED_CAPABILITIES.get(intent, [])
            missing = [c for c in needed if not capabilities.get(c)]
        return capability_missing_response(intent, missing), "capability_missing"

    if ev_status == "missing":
        return insufficient_evidence_response(intent), "insufficient_evidence"

    if ev_status == "unsafe":
        return out_of_scope_response(), "blocked_out_of_scope"

    # ── Evidence available — try LLM first, fall back to deterministic ───────
    if _USE_LLM and system_prompt and user_prompt:
        llm_answer = _try_llm_answer(system_prompt, user_prompt)
        if llm_answer:
            mode = "answered_with_document_evidence"
            return llm_answer, mode

    # Deterministic answer from evidence
    answer = _summarize_evidence(retrieval.evidence, intent, question)

    # Prepend partial evidence prefix if applicable
    if ev_status == "partial" and evidence_decision.limitations:
        mode = "answered_with_document_evidence"
    elif retrieval.evidence:
        mode = "answered_with_document_evidence"
    else:
        mode = "insufficient_evidence"

    return answer, mode
