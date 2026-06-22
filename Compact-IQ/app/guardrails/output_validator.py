"""
CompatIQ Output Validator
Validates the generated answer before returning it to the user.
Catches hallucinated facts, claimed capabilities, and unsafe content.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from app.guardrails.schemas import EvidenceItem


class OutputValidation(BaseModel):
    allowed: bool
    warnings: list[str]
    reason: str


_DEVICE_COMPLIANT_PATTERNS = [
    re.compile(r"\bdevice[s]?\s+is\s+(compliant|non-compliant|safe|at\s+risk)\b", re.I),
    re.compile(r"\ball\s+devices?\s+are\s+safe\b", re.I),
    re.compile(r"\b(srv|host|node)-\w+\s+is\s+(compliant|blocked|affected)\b", re.I),
    re.compile(r"\b\d+\s+devices?\s+violate\b", re.I),
    re.compile(r"\bfleet\s+(is|are)\s+(compliant|safe|ready)\b", re.I),
]

_APPROVED_CLAIM_PATTERNS = [
    re.compile(r"\bthis\s+rule\s+is\s+(active|live|in\s+production|approved\s+and\s+active)\b", re.I),
    re.compile(r"\bapproved\s+rule\s+is\s+enforced\b", re.I),
    re.compile(r"\bknowledge\s+graph\s+(contains|has|stored)\b", re.I),
    re.compile(r"\bcompliance\s+engine\s+(uses|has|applied)\b", re.I),
]

_KG_CLAIM_PATTERNS = [
    re.compile(r"\bthe\s+knowledge\s+graph\s+(shows?|confirms?|says?)\b", re.I),
    re.compile(r"\bkg\s+(path|traversal|shows?)\b", re.I),
    re.compile(r"\bgraph\s+(confirms?|shows?)\s+that\b", re.I),
]

_INVENTORY_CLAIM_PATTERNS = [
    re.compile(r"\binventory\s+(shows?|confirms?|says?)\b", re.I),
    re.compile(r"\bscanned\s+\d+\s+devices?\b", re.I),
]


def _extract_page_refs(text: str) -> list[str]:
    """Extract page number references from answer text."""
    return re.findall(r"\bpage\s+(\d+)\b", text, re.I)


def _extract_rule_ids(text: str) -> list[str]:
    """Extract rule ID references like COMP-001 from answer text."""
    return re.findall(r"\b(?:comp|unsup|rec|rcand)-\d+\b", text, re.I)


def validate_output(
    answer: str,
    intent: str,
    evidence: list[EvidenceItem],
    capabilities: dict[str, bool],
    scope_allowed: bool,
) -> OutputValidation:
    """Validate the generated answer for hallucinations and unsafe claims."""
    warnings: list[str] = []
    ans_lower = answer.lower()

    # ── 1. Inventory claims without inventory capability ─────────────────────
    if not capabilities.get("inventory"):
        for pattern in _DEVICE_COMPLIANT_PATTERNS:
            if pattern.search(answer):
                warnings.append(
                    "Answer claims device compliance/status but inventory is not connected."
                )
                break
        for pattern in _INVENTORY_CLAIM_PATTERNS:
            if pattern.search(answer):
                warnings.append(
                    "Answer references inventory data but inventory is not connected."
                )
                break

    # ── 2. Compliance claims without compliance capability ────────────────────
    if not capabilities.get("compliance_scan"):
        if re.search(r"\bcompliance\s+scan\s+(found|detected|shows?)\b", answer, re.I):
            warnings.append(
                "Answer references compliance scan results but scan is not connected."
            )

    # ── 3. KG claims without KG capability ───────────────────────────────────
    if not capabilities.get("knowledge_graph"):
        for pattern in _KG_CLAIM_PATTERNS:
            if pattern.search(answer):
                warnings.append(
                    "Answer references Knowledge Graph data but KG is not connected."
                )
                break

    # ── 4. Approved rule claims without approved_rules capability ─────────────
    if not capabilities.get("approved_rules"):
        for pattern in _APPROVED_CLAIM_PATTERNS:
            if pattern.search(answer):
                warnings.append(
                    "Answer claims a rule is active/approved in production, "
                    "but approved_rules repository is not connected."
                )
                break

    # ── 5. Page number references not backed by evidence ─────────────────────
    answer_pages = set(_extract_page_refs(answer))
    evidence_pages = set(
        str(ev.source_page) for ev in evidence if ev.source_page is not None
    )
    if answer_pages and not evidence_pages and len(evidence) > 0:
        # Some page refs in answer but none in evidence
        unretrieved_pages = answer_pages - evidence_pages
        if unretrieved_pages:
            warnings.append(
                f"Answer references page(s) {unretrieved_pages} not found in retrieved evidence."
            )

    # ── 6. Rule ID references not backed by evidence ──────────────────────────
    answer_ids = {r.upper() for r in _extract_rule_ids(answer)}
    evidence_ids = {
        ev.title.upper() for ev in evidence if ev.title
    } | {
        (ev.source_id or "").upper() for ev in evidence
    }
    # Only warn for very specific IDs that are not in evidence at all
    unretrieved_ids = answer_ids - evidence_ids
    if unretrieved_ids and intent in (
        "normalized_rule_lookup", "rule_candidate_lookup", "source_trace"
    ):
        warnings.append(
            f"Answer references rule ID(s) {unretrieved_ids} not found in retrieved evidence. "
            "Verify these are correct."
        )

    # ── 7. Out-of-scope content in answer ─────────────────────────────────────
    oos_markers = [
        "here is a joke", "here's a joke", "let me tell you a joke",
        "the weather", "who won", "cricket match", "football game"
    ]
    if any(m in ans_lower for m in oos_markers):
        return OutputValidation(
            allowed=False,
            warnings=["Answer contains out-of-scope content."],
            reason="Answer was rejected: contains out-of-scope response.",
        )

    # ── 8. Internal prompt disclosure ────────────────────────────────────────
    if "system instruction" in ans_lower and "strict rules" in ans_lower:
        return OutputValidation(
            allowed=False,
            warnings=["Answer discloses internal system instructions."],
            reason="Answer rejected: internal policy disclosure.",
        )

    # ── Final decision ────────────────────────────────────────────────────────
    if warnings:
        # Warnings don't block — they are surfaced to the caller as metadata
        return OutputValidation(
            allowed=True,
            warnings=warnings,
            reason=f"Answer passed validation with {len(warnings)} warning(s).",
        )

    return OutputValidation(
        allowed=True,
        warnings=[],
        reason="Answer passed all validation checks.",
    )
