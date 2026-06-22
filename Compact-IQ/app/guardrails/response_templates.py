"""
CompatIQ Response Templates
Standard refusal and limitation messages used when evidence is insufficient
or capabilities are missing.
"""
from __future__ import annotations


def out_of_scope_response() -> str:
    return (
        "I'm the CompatIQ assistant. I can help with compatibility rules, "
        "document evidence, rollout readiness, rule review, device compliance, "
        "and remediation guidance within CompatIQ. I can't answer unrelated questions."
    )


def prompt_injection_response() -> str:
    return (
        "I'm the CompatIQ assistant. I can only answer questions related to "
        "compatibility rules, document evidence, and compliance reasoning. "
        "I cannot change my instructions or answer off-topic questions."
    )


def capability_missing_response(intent: str, missing_capabilities: list[str]) -> str:
    cap_names = {
        "knowledge_graph": "Knowledge Graph traversal",
        "knowledge_base": "Knowledge Base semantic retrieval",
        "inventory": "device inventory",
        "compliance_scan": "compliance scan results",
        "remediation_engine": "remediation engine",
        "approved_rules": "approved rule repository",
    }
    readable = [cap_names.get(c, c) for c in missing_capabilities]
    cap_str = " and ".join(readable) if readable else "the required module"

    return (
        f"That question is related to CompatIQ, but it requires {cap_str}. "
        "I can currently answer from Document Intelligence evidence such as uploaded "
        "documents, source chunks, and rule candidates. When the required module is "
        "connected, I will be able to answer this question fully."
    )


def insufficient_evidence_response(intent: str) -> str:
    return (
        "I could not find enough evidence in the current CompatIQ data to answer that. "
        "Please upload or process the relevant document, or review the extracted rule "
        "candidate first, then ask again."
    )


def partial_evidence_prefix() -> str:
    return (
        "I found related evidence, but it has some limitations. "
        "Please review the evidence below and note the limitations listed."
    )


def general_concept_response(question: str) -> str:
    q = question.strip().lower()

    # ── Specific concept definitions ──────────────────────────────────────────
    if "minimum version" in q or "min version" in q:
        return (
            "A **minimum version rule** (rule_type: `min_version_constraint`) is a "
            "compatibility rule that states a component must be at or above a specific "
            "version to be compatible with another component. For example: "
            "'System BIOS must be >= 6.4.2 when running Platform Driver Pack 5.7.0.' "
            "These rules are extracted from vendor release notes and normalized with "
            "version schemes (semantic, build, firmware)."
        )
    if "rule candidate" in q or "candidate" in q:
        return (
            "A **rule candidate** is a compatibility constraint extracted from a document "
            "by the LLM pipeline. Candidates are raw extractions that require human review "
            "before they become approved rules. Each candidate has: a rule type, conditions, "
            "requirements, a confidence score, a source excerpt, and a review status "
            "(pending_review / approved / rejected / needs_clarification)."
        )
    if "normali" in q:
        return (
            "**Normalization** is the process of converting raw LLM rule extractions into "
            "a structured, canonical format. It maps aliases (e.g., 'Win Server 2016' → "
            "'windows_server_2016'), standardizes operators (≥, >, =), and assigns version "
            "schemes (semantic, build, firmware). Normalized candidates are stored in "
            "`normalized_rule_json` and are ready for human review and KB/KG promotion."
        )
    if "enforcement" in q or "enforcement_type" in q:
        return (
            "**Enforcement type** indicates how strictly a compatibility rule applies. "
            "Common types: `required` (must comply), `recommended` (best practice), "
            "`conditional` (applies only under certain conditions). "
            "Rules with explicit enforcement language ('must', 'required', 'shall') "
            "are typically classified as `required`."
        )
    if "confidence" in q:
        return (
            "**Confidence score** (0.0–1.0) represents how certain the LLM was when "
            "extracting a rule. High confidence (≥ 0.85): explicit language found. "
            "Medium (0.65–0.84): implied requirement. Low (< 0.65): ambiguous evidence. "
            "The score also drives the tiering system: high-confidence rules can be "
            "auto-approved, while low-confidence rules require individual human review."
        )
    if "tier" in q:
        return (
            "The **tiering system** in CompatIQ groups rule candidates by how much human "
            "attention they need:\n"
            "- **Individual tier** (red): Low confidence or quality warnings — each rule "
            "needs a structured individual decision.\n"
            "- **Batch tier** (amber): Medium confidence — can be batch-approved with one "
            "review per group.\n"
            "- **Auto tier** (green): High confidence, explicit enforcement, no warnings — "
            "automatically approved on page load."
        )
    if "source excerpt" in q or "excerpt" in q:
        return (
            "A **source excerpt** is the exact text passage from the source document that "
            "the LLM used as evidence when extracting a rule candidate. Source excerpts "
            "provide the human reviewer with traceable evidence: which document, which page, "
            "and which exact sentence justified the extracted rule."
        )
    if "chunk" in q:
        return (
            "A **document chunk** is a semantic unit of text extracted from an uploaded "
            "document during the chunking phase. Chunks are classified by type (e.g., "
            "`requirement_rule`, `section_title`, `document_metadata`, `table_row`) and "
            "scored for rule likelihood (high/medium/low). High-likelihood chunks are "
            "sent to the LLM for rule extraction."
        )
    if "handoff" in q or "promotion" in q:
        return (
            "**Handoff/Promotion** is the process of sending approved rule candidates "
            "to downstream modules (Knowledge Base, Knowledge Graph, Compliance engine). "
            "In CompatIQ, a candidate must be reviewed and approved before it can be "
            "promoted. The current implementation supports marking candidates as 'staged' "
            "before final promotion to the approved rule repository."
        )

    # Generic fallback
    return (
        "That is a general compatibility and CompatIQ concept. CompatIQ processes "
        "vendor documents through a pipeline: upload → profile → extract chunks → "
        "LLM rule extraction → normalization → human review → KB/KG promotion. "
        "The assistant can answer questions about each of these phases using available "
        "document evidence, rule candidates, and review status data."
    )


def capability_question_response() -> str:
    return (
        "I'm the CompatIQ Guarded Assistant. I can currently answer questions about:\n\n"
        "**Available (Document Intelligence Mode):**\n"
        "- Uploaded documents and their metadata\n"
        "- Extracted document chunks and source excerpts\n"
        "- Raw and normalized rule candidates\n"
        "- Rule review status (pending, approved, rejected)\n"
        "- Known issues and unsupported configurations\n"
        "- Remediation guidance found in documents\n"
        "- General compatibility concepts\n\n"
        "**Not yet connected (answer will include limitation):**\n"
        "- Device inventory and fleet status\n"
        "- Compliance scan results and violations\n"
        "- Knowledge Graph traversal and root cause analysis\n"
        "- Knowledge Base semantic search for approved rules\n\n"
        "Try asking: 'What rules were extracted from this document?' or "
        "'What does COMP-006 say?' or 'What candidates are pending review?'"
    )
