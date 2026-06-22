"""
CompatIQ Guardrail Capability Matrix
Controls which backend subsystems are currently available.
Driven by env flags to allow future KG/KB/inventory plug-in without code changes.
"""
from __future__ import annotations

import os


DEFAULT_CAPABILITIES: dict[str, bool] = {
    "document_intelligence": True,
    "rule_candidates": True,
    "review_status": True,
    "approved_rules": False,
    "knowledge_base": False,
    "knowledge_graph": False,
    "inventory": False,
    "compliance_scan": False,
    "remediation_engine": False,
    "audit_log": True,
}

# Env-flag names → capability keys
_ENV_FLAGS: dict[str, str] = {
    "GUARDRAILS_KB_ENABLED": "knowledge_base",
    "GUARDRAILS_KG_ENABLED": "knowledge_graph",
    "GUARDRAILS_INVENTORY_ENABLED": "inventory",
    "GUARDRAILS_COMPLIANCE_ENABLED": "compliance_scan",
    "GUARDRAILS_REMEDIATION_ENABLED": "remediation_engine",
    "GUARDRAILS_APPROVED_RULES_ENABLED": "approved_rules",
}


def get_current_capabilities() -> dict[str, bool]:
    """Return the current capability state, applying any env-flag overrides.

    This is the single source of truth for what subsystems are connected.
    When a teammate finishes the KB or KG adapter, they set the matching env
    flag and the guardrail layer picks it up automatically.
    """
    caps = dict(DEFAULT_CAPABILITIES)
    for env_key, cap_key in _ENV_FLAGS.items():
        raw = os.environ.get(env_key, "").strip().lower()
        if raw in ("true", "1", "yes"):
            caps[cap_key] = True
        elif raw in ("false", "0", "no"):
            caps[cap_key] = False
    return caps


# Intent → required capabilities mapping
INTENT_REQUIRED_CAPABILITIES: dict[str, list[str]] = {
    "document_summary": ["document_intelligence"],
    "document_metadata_lookup": ["document_intelligence"],
    "chunk_evidence_lookup": ["document_intelligence"],
    "rule_candidate_lookup": ["rule_candidates"],
    "normalized_rule_lookup": ["rule_candidates"],
    "source_trace": ["document_intelligence", "rule_candidates"],
    "review_status_lookup": ["review_status"],
    "remediation_from_document": ["document_intelligence"],
    "known_issue_lookup": ["document_intelligence"],
    "unsupported_config_lookup": ["document_intelligence", "rule_candidates"],
    "compatibility_explanation": ["document_intelligence"],
    "general_compatibility_concept": [],          # No retrieval needed
    "handoff_status": ["document_intelligence"],
    "capability_question": [],
    "requires_kb": ["knowledge_base"],
    "requires_kg": ["knowledge_graph"],
    "requires_inventory": ["inventory"],
    "requires_compliance_scan": ["compliance_scan"],
    "out_of_scope": [],
    # Future intents — will become real when KB/KG are connected
    "approved_rule_lookup": ["approved_rules"],
    "device_compliance_status": ["inventory", "compliance_scan"],
    "violation_explanation": ["inventory", "compliance_scan", "knowledge_graph"],
    "root_cause_analysis": ["knowledge_graph"],
    "affected_device_query": ["inventory", "compliance_scan"],
    "rollout_readiness_query": ["inventory", "compliance_scan"],
    "fleet_remediation_plan": ["inventory", "compliance_scan", "remediation_engine"],
    "kg_path_query": ["knowledge_graph"],
}
