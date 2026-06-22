"""
CompatIQ Prompt Builder
Builds a grounded LLM prompt from retrieved evidence.
The system instruction prevents hallucination and grounds the LLM
to only the supplied evidence context.
"""
from __future__ import annotations

from app.guardrails.evidence_checker import EvidenceDecision
from app.guardrails.schemas import EvidenceItem, RetrievalResult

SYSTEM_INSTRUCTION = """You are CompatIQ Assistant, a bounded compatibility reasoning agent.

STRICT RULES — you MUST follow these:
1. Answer ONLY using the evidence provided in the context below.
2. Do NOT use outside knowledge, training data, or general internet knowledge.
3. Do NOT invent rule IDs, version numbers, source pages, device names, or component versions.
4. Do NOT claim that any rule is "active", "in production", or "in the compliance engine" — candidates are candidates, not approved rules.
5. If a rule is a candidate with review_status "pending_review", call it "pending candidate" — not an approved rule.
6. Do NOT claim any device is compliant or non-compliant — inventory/compliance is not connected.
7. Do NOT provide remediation steps unless the retrieved evidence explicitly contains remediation guidance.
8. If the evidence is insufficient, say so clearly and explain what is missing.
9. ALWAYS mention the source document ID, source page, rule ID, or candidate ID when available.
10. If limitations are present, disclose them clearly in your answer.

You are an expert in enterprise IT compatibility, firmware versioning, BIOS requirements,
driver packs, OS compatibility matrices, and compliance evidence tracing."""


def _format_evidence_block(items: list[EvidenceItem]) -> str:
    """Format evidence items into a readable context block for the LLM."""
    if not items:
        return "No evidence retrieved."

    lines: list[str] = []
    for i, ev in enumerate(items[:8], 1):
        lines.append(f"\n--- Evidence Item {i} ---")
        lines.append(f"Type: {ev.source_type}")
        if ev.title:
            lines.append(f"Title/ID: {ev.title}")
        if ev.source_id:
            lines.append(f"Source ID: {ev.source_id}")
        if ev.source_document_id:
            lines.append(f"Document: {ev.source_document_id}")
        if ev.source_page:
            lines.append(f"Page: {ev.source_page}")
        if ev.review_status:
            lines.append(f"Review Status: {ev.review_status}")
        if ev.confidence is not None:
            lines.append(f"Confidence: {ev.confidence:.2f}")
        if ev.source_excerpt:
            lines.append(f"Source Excerpt: \"{ev.source_excerpt[:400]}\"")
        if ev.text and ev.text != ev.source_excerpt:
            lines.append(f"Content: {ev.text[:300]}")
        if ev.metadata.get("rule_type"):
            lines.append(f"Rule Type: {ev.metadata['rule_type']}")
        if ev.metadata.get("severity"):
            lines.append(f"Severity: {ev.metadata['severity']}")
        if ev.metadata.get("normalized_rule"):
            lines.append(f"Normalized Rule: {str(ev.metadata['normalized_rule'])[:400]}")

    return "\n".join(lines)


def build_grounded_prompt(
    question: str,
    intent: str,
    evidence_decision: EvidenceDecision,
    retrieval: RetrievalResult,
    capabilities: dict[str, bool],
    limitations: list[str],
) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for grounded LLM answer generation.

    Returns a tuple of (system_instruction, user_message).
    """
    evidence_block = _format_evidence_block(retrieval.evidence)

    cap_summary_lines = []
    if not capabilities.get("inventory"):
        cap_summary_lines.append("- Inventory: NOT connected (do not claim device status)")
    if not capabilities.get("compliance_scan"):
        cap_summary_lines.append("- Compliance Scan: NOT connected (do not claim violation status)")
    if not capabilities.get("knowledge_graph"):
        cap_summary_lines.append("- Knowledge Graph: NOT connected (do not claim KG traversal)")
    if not capabilities.get("knowledge_base"):
        cap_summary_lines.append("- Knowledge Base: NOT connected (do not claim approved rule lookup)")
    cap_summary = "\n".join(cap_summary_lines) if cap_summary_lines else "All relevant systems connected."

    lim_text = ""
    if limitations:
        lim_text = "\n\nKNOWN LIMITATIONS:\n" + "\n".join(f"- {l}" for l in limitations)

    user_prompt = f"""INTENT: {intent}
EVIDENCE STATUS: {evidence_decision.status}

CURRENTLY UNAVAILABLE SUBSYSTEMS:
{cap_summary}

RETRIEVED EVIDENCE:
{evidence_block}
{lim_text}

USER QUESTION:
{question}

Please answer the question using ONLY the evidence provided above.
Cite source IDs, page numbers, and document IDs where available.
If the evidence is partial or limited, include a clear disclosure."""

    return SYSTEM_INSTRUCTION, user_prompt
