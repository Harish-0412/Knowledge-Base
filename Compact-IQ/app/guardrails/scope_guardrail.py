"""
CompatIQ Scope Guardrail
Deterministic domain-scope check: is this question related to CompatIQ?

Approach:
  1. Check for prompt injection / unsafe patterns → block immediately.
  2. Check for obvious out-of-scope topics → block unless compat terms also present.
  3. Check for in-scope CompatIQ/compatibility terms → allow.
  4. Fallback: allow (lean permissive for general compatibility concepts).
"""
from __future__ import annotations

import re

from pydantic import BaseModel


# ── Keyword sets ──────────────────────────────────────────────────────────────

_IN_SCOPE_KEYWORDS: set[str] = {
    "compatibility", "compatible", "incompatible", "compliance", "compliant",
    "rule", "rules", "candidate", "candidates", "document", "documents",
    "release note", "release notes", "evidence", "source", "chunk", "chunks",
    "page", "excerpt", "firmware", "bios", "driver", "drivers",
    "os", "operating system", "windows server", "windows",
    "tpm", "secure boot", "secureboot", "uefi",
    "crowdstrike", "intune", "nvidia", "vgpu", "nic", "ethernet",
    "remediation", "upgrade", "rollout", "configuration", "configure",
    "unsupported", "supported", "certified", "baseline", "known issue",
    "approval", "approve", "review", "reject", "reviewed",
    "rule extraction", "normalize", "normalization", "validated",
    "pending review", "approved candidate", "rule candidate",
    "inventory", "device", "server", "host", "scan", "violation",
    "version", "version constraint", "min version", "minimum version",
    "dependency", "requirement", "handoff", "export",
    "comp-", "unsup-", "rec-", "rcand-", "doc-",
    "perc", "storecli", "openmanage", "dell", "idrac",
    "esxi", "vmware", "hyper-v", "linux", "ubuntu", "rhel", "centos",
    "poweredge", "proliant", "thinkserver",
    "kb", "knowledge base", "kg", "knowledge graph", "graph",
    "llm", "ai", "extraction", "extracted",
    "compatiq",
}

_OUT_OF_SCOPE_KEYWORDS: set[str] = {
    "cricket", "football", "soccer", "basketball", "baseball", "tennis",
    "sports", "match", "tournament", "championship", "league", "nfl", "ipl",
    "movie", "movies", "film", "actor", "actress", "celebrity",
    "recipe", "cook", "bake", "ingredient", "restaurant",
    "weather", "forecast", "rain", "temperature",
    "politics", "election", "vote", "president", "prime minister",
    "love letter", "poem", "poetry", "story", "creative writing",
    "photosynthesis", "biology", "chemistry", "physics", "algebra",
    "homework", "essay", "school", "university", "college",
    "joke", "funny", "humor", "comedy",
    "stocks", "bitcoin", "crypto", "nft", "investment",
    "medical advice", "diagnosis", "symptom", "medicine",
    "lawyer", "legal advice",
}

_PROMPT_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(your\s+)?(previous|prior|all|above)\s+instructions?", re.I),
    re.compile(r"forget\s+(your\s+)?(previous|prior|all)?\s*(rules?|instructions?)", re.I),
    re.compile(r"you\s+are\s+now\s+a\s+(general|different|new)", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.I),
    re.compile(r"show\s+(me\s+)?(your\s+)?(hidden|internal|system)\s*(prompt|instructions?)", re.I),
    re.compile(r"bypass\s+(the\s+)?(guardrail|filter|safety|restriction)", re.I),
    re.compile(r"pretend\s+you\s+(are|have\s+no)\s+restrictions?", re.I),
    re.compile(r"act\s+as\s+(if\s+you\s+are\s+)?a\s+general", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"dan\s+(mode|prompt)", re.I),
]


class ScopeDecision(BaseModel):
    allowed: bool
    reason: str
    confidence: float
    is_injection: bool = False


def check_scope(question: str) -> ScopeDecision:
    """Determine whether the question is in scope for the CompatIQ assistant.

    Returns a ScopeDecision with allowed=True or False and a reason string.
    """
    q = question.strip().lower()

    # 1. Prompt injection detection — always blocked, marked unsafe
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(q):
            return ScopeDecision(
                allowed=False,
                reason="Prompt injection or unsafe instruction detected.",
                confidence=1.0,
                is_injection=True,
            )

    # 2. Collect keyword hits
    in_scope_hits = [kw for kw in _IN_SCOPE_KEYWORDS if kw in q]
    out_scope_hits = [kw for kw in _OUT_OF_SCOPE_KEYWORDS if kw in q]

    # 3. In-scope signal present → allow
    if in_scope_hits:
        return ScopeDecision(
            allowed=True,
            reason=f"In-scope keywords detected: {', '.join(in_scope_hits[:5])}",
            confidence=min(0.6 + 0.08 * len(in_scope_hits), 0.99),
        )

    # 4. Pure out-of-scope, no compat terms → block
    if out_scope_hits:
        return ScopeDecision(
            allowed=False,
            reason=f"Out-of-scope topic detected: {', '.join(out_scope_hits[:3])}",
            confidence=min(0.7 + 0.1 * len(out_scope_hits), 0.99),
        )

    # 5. Short/ambiguous question with no signal — allow with low confidence
    #    (general compatibility concepts like "what is a rule?" may not hit keywords)
    return ScopeDecision(
        allowed=True,
        reason="No strong out-of-scope signal detected; allowing as potential compatibility question.",
        confidence=0.5,
    )
