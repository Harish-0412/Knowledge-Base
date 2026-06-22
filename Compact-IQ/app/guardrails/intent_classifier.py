"""
CompatIQ Intent Classifier
Deterministic rule-based intent classification.

Each intent check is a ranked predicate over the lower-cased question.
The first match wins, in priority order.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from app.guardrails.capabilities import INTENT_REQUIRED_CAPABILITIES


class IntentDecision(BaseModel):
    intent: str
    confidence: float
    reason: str
    required_capabilities: list[str]


# ── Helper ────────────────────────────────────────────────────────────────────

def _kws(*words: str):
    """Return True-check: any of the words is in the question string."""
    return lambda q: any(w in q for w in words)


def _re(*patterns: str):
    compiled = [re.compile(p, re.I) for p in patterns]
    return lambda q: any(p.search(q) for p in compiled)


# ── Ranked intent predicates ──────────────────────────────────────────────────
# Format: (intent_name, confidence, test_fn, reason)

_RULES: list[tuple[str, float, object, str]] = [

    # ── Out-of-scope / unsafe (but scope guard already handles hard blocks) ──
    ("out_of_scope",
     0.98,
     _kws("joke", "love letter", "cricket", "football", "basketball", "weather",
          "photosynthesis", "recipe", "politics", "homework", "story"),
     "Unrelated topic keyword"),

    # ── Inventory / device queries ────────────────────────────────────────────
    ("requires_inventory",
     0.95,
     _re(r"\bdevice[s]?\b.*\b(comply|compli|violat|status|compliant|blocked|affect)",
         r"\b(which|what|list)\b.*\bdevice[s]?\b",
         r"\bfleet\b",
         r"\bsrv-\w+",
         r"\bhost[s]?\b.*\b(violat|compli|affect|block)"),
     "Device/fleet query requiring inventory"),

    # ── Compliance scan ───────────────────────────────────────────────────────
    ("requires_compliance_scan",
     0.95,
     _re(r"\b(compliance\s+scan|scan\s+result|compliance\s+result|violation[s]?)\b",
         r"\b(non-compliant|out.of.spec|policy\s+failure)\b",
         r"\brollout\s+readiness\b",
         r"\bwhich\s+(devices?|hosts?|servers?)\s+(violat|fail|block)"),
     "Compliance scan / violation query"),

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    ("requires_kg",
     0.95,
     _kws("knowledge graph", "kg", "graph path", "root cause", "dependency chain",
          "kg path", "causality", "dependency graph", "node", "edge", "traversal",
          "graph traversal"),
     "Knowledge Graph traversal query"),

    # ── Knowledge Base ────────────────────────────────────────────────────────
    ("requires_kb",
     0.93,
     _kws("knowledge base", "kb", "semantic search", "approved rule repository",
          "canonical rule", "pgvector"),
     "Knowledge Base retrieval query"),

    # ── Review status ─────────────────────────────────────────────────────────
    ("review_status_lookup",
     0.92,
     _re(r"\b(pending|approved|rejected|staged|clarif)\b.*\b(candidate|rule|review)\b",
         r"\b(which|what|list|show)\b.{0,40}(pending|approved|rejected|staged)\b",
         r"\b(review\s+status|review\s+queue|awaiting\s+review)\b",
         r"\b(candidates?)\b.{0,30}\b(approved|rejected|pending)\b"),
     "Review status / approval queue lookup"),

    # ── Source trace / evidence lookup ────────────────────────────────────────
    ("source_trace",
     0.90,
     _re(r"\b(source|evidence|trace|where\s+(does|is|was|did))\b.{0,50}"
         r"\b(come\s+from|found|extracted|located|page|excerpt)\b",
         r"\b(page\s+\d+|source\s+page|source\s+document|source\s+excerpt)\b",
         r"\bshow\s+(me\s+)?(the\s+)?evidence\b",
         r"\bwhere\s+(is\s+this\s+rule|did\s+this\s+come\s+from)\b"),
     "Source/evidence trace"),

    # ── Chunk evidence lookup ─────────────────────────────────────────────────
    ("chunk_evidence_lookup",
     0.90,
     _re(r"\b(show|find|get|display)\b.{0,30}\b(evidence|chunk|excerpt|passage)\b",
         r"\bevidence\s+for\b",
         r"\b(tpm|bios|firmware|nic|nvidia|crowdstrike|intune|secure\s+boot)"
         r".{0,40}\b(evidence|excerpt|source|chunk)\b"),
     "Document chunk / evidence lookup"),

    # ── Normalized rule lookup ────────────────────────────────────────────────
    ("normalized_rule_lookup",
     0.90,
     _re(r"\b(comp-\d+|unsup-\d+|rec-\d+|rcand-\d+)\b",
         r"\bwhat\s+does\b.{0,40}\b(comp|unsup|rec|rcand)-\d+",
         r"\b(explain|describe|tell\s+me\s+about)\b.{0,40}\b(rule|candidate)\b",
         r"\bnormalized\s+rule\b"),
     "Normalized rule or candidate lookup by ID"),

    # ── Rule candidate lookup ─────────────────────────────────────────────────
    ("rule_candidate_lookup",
     0.88,
     _re(r"\b(rule\s+candidate[s]?|raw\s+candidate[s]?)\b",
         r"\b(extracted|list|show)\b.{0,30}\b(rule[s]?|candidate[s]?)\b",
         r"\bwhat\s+rules?\s+were\s+extracted\b",
         r"\bextracted\s+rule[s]?\b"),
     "Rule candidate listing or lookup"),

    # ── Unsupported config ────────────────────────────────────────────────────
    ("unsupported_config_lookup",
     0.88,
     _re(r"\b(unsupported|not\s+supported|excluded|incompatible)\b.{0,50}"
         r"\b(config|configuration|combination|device|rule)\b",
         r"\bunsup-\d+\b",
         r"\bwhat\s+(configuration[s]?|combination[s]?)\s+(is|are|were)"
         r"\s+(not\s+supported|unsupported|excluded|incompatible)\b"),
     "Unsupported configuration lookup"),

    # ── Remediation from document ─────────────────────────────────────────────
    ("remediation_from_document",
     0.87,
     _re(r"\b(remediation|remediate|fix|resolve|workaround|required\s+action"
         r"|recommended\s+action|how\s+to\s+(fix|resolve|upgrade))\b",
         r"\b(upgrade|update)\b.{0,30}\b(bios|firmware|driver|os|version)\b",
         r"\bwhat\s+should\s+(i|we)\s+do\b",
         r"\bhow\s+(can|do)\s+(i|we)\s+(fix|resolve|address|handle)\b"),
     "Remediation guidance from document evidence"),

    # ── Known issue ───────────────────────────────────────────────────────────
    ("known_issue_lookup",
     0.86,
     _re(r"\b(known\s+issue[s]?|known\s+problem[s]?|limitation[s]?|caveat[s]?)\b",
         r"\bwhat\s+(issue[s]?|problem[s]?|bug[s]?)\b.{0,40}\bdocument\b"),
     "Known issue lookup"),

    # ── Document summary ──────────────────────────────────────────────────────
    ("document_summary",
     0.85,
     _re(r"\b(summar(y|ize)|overview|what\s+is\s+this\s+document|"
         r"what\s+does\s+this\s+document\s+(cover|contain|say)|"
         r"document\s+summary|brief\s+(me|description))\b"),
     "Document summary / overview"),

    # ── Document metadata ─────────────────────────────────────────────────────
    ("document_metadata_lookup",
     0.84,
     _re(r"\b(document\s+(id|metadata|version|date|type|vendor|platform|status)|"
         r"when\s+was\s+(this\s+)?(document|doc)\s+(uploaded|created)|"
         r"what\s+(vendor|platform|product)\s+(is\s+this|does\s+this)\s+document"
         r"|(doc-[a-f0-9]+))\b",
         r"\bdoc-[a-f0-9]{6,}\b"),
     "Document metadata lookup"),

    # ── Handoff status ────────────────────────────────────────────────────────
    ("handoff_status",
     0.83,
     _kws("handoff", "hand off", "promote", "promotion", "next stage",
          "send to", "downstream", "teammate", "member", "integration"),
     "Handoff / promotion status query"),

    # ── Capability question ───────────────────────────────────────────────────
    ("capability_question",
     0.82,
     _re(r"\b(what\s+can\s+(you|this\s+(assistant|system))\s+(do|answer|help|tell))\b",
         r"\b(capabilit(y|ies)|feature[s]?|supported\s+question[s]?)\b",
         r"\bwhat\s+questions?\s+(can|do)\s+(you|this)\s+(answer|handle)\b"),
     "Assistant capability / help question"),

    # ── General compatibility concept ─────────────────────────────────────────
    ("general_compatibility_concept",
     0.80,
     _re(r"\bwhat\s+is\s+(a\s+)?(rule|candidate|compatibility|minimum\s+version"
         r"|enforcement|normalization|confidence|source\s+excerpt|tier|"
         r"rule\s+type|condition|requirement)\b",
         r"\b(explain|define|describe)\s+(what|the\s+term)?\s*(rule|candidate|"
         r"compatibility|normalization|enforcement|confidence|tier)\b",
         r"\bhow\s+(does|do)\s+(rule|candidate|compatibility|normalization|"
         r"enforcement|tier)\s+(work|function)\b"),
     "General compatibility concept explanation"),
]


def classify_intent(question: str) -> IntentDecision:
    """Classify the intent of an in-scope user question.

    Uses deterministic rule matching in priority order.
    Returns the first matched intent.
    """
    q = question.strip().lower()

    for intent, confidence, test_fn, reason in _RULES:
        if test_fn(q):
            return IntentDecision(
                intent=intent,
                confidence=confidence,
                reason=reason,
                required_capabilities=INTENT_REQUIRED_CAPABILITIES.get(intent, []),
            )

    # Default fallback: treat as a general compatibility concept
    return IntentDecision(
        intent="general_compatibility_concept",
        confidence=0.5,
        reason="No specific intent pattern matched; treating as general concept.",
        required_capabilities=[],
    )
