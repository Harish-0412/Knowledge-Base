"""
CompatIQ Guardrail Audit Logger
Logs every guarded query decision to storage/guardrail_audit.jsonl.
Does NOT log API keys, internal prompts, or sensitive system instructions.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_AUDIT_LOG_PATH = Path(os.environ.get("GUARDRAIL_AUDIT_LOG", "storage/guardrail_audit.jsonl"))


def log_guardrail_event(
    question: str,
    document_id: str | None,
    candidate_id: str | None,
    scope_allowed: bool,
    intent: str,
    required_capabilities: list[str],
    available_capabilities: dict[str, bool],
    retrievers_used: list[str],
    evidence_count: int,
    evidence_status: str,
    response_mode: str,
    blocked: bool,
    block_reason: str | None,
    warnings: list[str],
    answer_preview: str,
) -> None:
    """Append one guardrail audit record to the JSONL log file.

    Fields are carefully chosen: no API keys, no internal prompts,
    no sensitive hidden instructions.
    """
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "question": question[:500],             # Truncate long questions
        "document_id": document_id,
        "candidate_id": candidate_id,
        "scope_allowed": scope_allowed,
        "intent": intent,
        "required_capabilities": required_capabilities,
        "available_capabilities": {
            k: v for k, v in available_capabilities.items()
            # Exclude keys that could hint at infrastructure details
            if k not in ("audit_log",)
        },
        "retrievers_used": retrievers_used,
        "evidence_count": evidence_count,
        "evidence_status": evidence_status,
        "response_mode": response_mode,
        "blocked": blocked,
        "block_reason": block_reason,
        "output_validation_warnings": warnings,
        "final_answer_preview": answer_preview[:200],
    }

    try:
        _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        # Audit logging must never crash the main request path
        logger.warning("Guardrail audit logging failed: %s", exc)

    # Also log at DEBUG level for server log visibility
    logger.debug(
        "Guardrail audit: intent=%s mode=%s blocked=%s evidence=%d",
        intent, response_mode, blocked, evidence_count,
    )
