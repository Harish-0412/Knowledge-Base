"""
CompatIQ Guardrail Service
Orchestrates the full 10-step guarded assistant pipeline.

Pipeline:
  1.  Capture request metadata
  2.  Check domain scope
  3.  If blocked → return out_of_scope / blocked_unsafe
  4.  Classify intent
  5.  Get current capabilities
  6.  Route retrieval by intent
  7.  Check evidence sufficiency
  8.  Build grounded prompt (for LLM mode)
  9.  Generate answer (deterministic or LLM)
  10. Validate output
  11. Log guardrail audit
  12. Return structured response
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.guardrails.answer_generator import generate_answer
from app.guardrails.audit_logger import log_guardrail_event
from app.guardrails.capabilities import INTENT_REQUIRED_CAPABILITIES, get_current_capabilities
from app.guardrails.evidence_checker import check_evidence
from app.guardrails.intent_classifier import classify_intent
from app.guardrails.output_validator import validate_output
from app.guardrails.prompt_builder import build_grounded_prompt
from app.guardrails.retrieval_router import retrieve_for_intent
from app.guardrails.schemas import GuardedQueryRequest, GuardedQueryResponse
from app.guardrails.scope_guardrail import check_scope

logger = logging.getLogger(__name__)

# ── Suggested next actions by response mode ───────────────────────────────────

_NEXT_ACTIONS: dict[str, list[str]] = {
    "blocked_out_of_scope": [
        "Ask about a compatibility rule, document, source evidence, or review status.",
        "Example: 'What does COMP-001 say?'",
        "Example: 'What candidates are pending review?'",
    ],
    "blocked_unsafe": [
        "Please rephrase your question to relate to CompatIQ compatibility data.",
    ],
    "capability_missing": [
        "Ask about available Document Intelligence evidence instead.",
        "Example: 'What rules were extracted from this document?'",
        "Example: 'Show evidence for BIOS version requirements.'",
    ],
    "insufficient_evidence": [
        "Upload or process the relevant document first.",
        "Review the extracted rule candidates for this document.",
        "Try a broader search term or omit the specific version number.",
    ],
    "answered_with_document_evidence": [
        "Open the source document in the Documents page to see the full context.",
        "Review the matching candidates in the Rule Review Queue.",
        "Approve candidates to promote them to the next stage.",
    ],
    "answered_general_concept": [
        "Ask about a specific rule: 'What does COMP-001 say?'",
        "Ask about evidence: 'Show evidence for TPM Firmware 7.2.4.1'",
        "Ask about review status: 'Which candidates are pending review?'",
    ],
    "needs_human_review": [
        "Open the Rule Review Queue to review pending candidates.",
        "Approve or reject candidates individually or in batch.",
    ],
}


class GuardrailService:
    """Main guarded assistant pipeline orchestrator."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def answer(self, request: GuardedQueryRequest) -> GuardedQueryResponse:
        """Run the full 10-step guardrail pipeline and return a structured response."""
        question = request.question.strip()

        # ── Step 1: Capability matrix ─────────────────────────────────────────
        capabilities = get_current_capabilities()

        # ── Step 2: Scope check ───────────────────────────────────────────────
        scope = check_scope(question)

        # ── Step 3: Early exit for blocked / injection ────────────────────────
        if not scope.allowed:
            intent = "out_of_scope"
            if scope.is_injection:
                mode = "blocked_unsafe"
            else:
                mode = "blocked_out_of_scope"

            from app.guardrails.response_templates import (
                out_of_scope_response,
                prompt_injection_response,
            )
            answer_text = (
                prompt_injection_response() if scope.is_injection
                else out_of_scope_response()
            )

            self._log(
                request=request,
                intent=intent,
                capabilities=capabilities,
                retrievers_used=[],
                evidence_count=0,
                evidence_status="unsafe",
                response_mode=mode,
                blocked=True,
                block_reason=scope.reason,
                warnings=[],
                answer_text=answer_text,
                scope_allowed=False,
            )

            return GuardedQueryResponse(
                allowed=False,
                intent=intent,
                mode=mode,
                answer=answer_text,
                evidence_used=[],
                limitations=[],
                suggested_next_actions=_NEXT_ACTIONS.get(mode, []),
                guardrail_trace=self._build_trace(
                    request, scope, intent, None, None, mode, [], [], capabilities
                ) if request.include_guardrail_trace else {},
            )

        # ── Step 4: Intent classification ─────────────────────────────────────
        intent_decision = classify_intent(question)
        intent = intent_decision.intent

        # ── Step 5: Retrieval ─────────────────────────────────────────────────
        retrieval = retrieve_for_intent(request, intent, capabilities, self._db)

        # ── Step 6: Evidence check ────────────────────────────────────────────
        evidence_decision = check_evidence(intent, retrieval, capabilities, scope_allowed=True)

        # ── Step 7: Build grounded prompt (for LLM mode) ──────────────────────
        all_limitations = list(evidence_decision.limitations) + list(retrieval.warnings)
        system_prompt, user_prompt = build_grounded_prompt(
            question=question,
            intent=intent,
            evidence_decision=evidence_decision,
            retrieval=retrieval,
            capabilities=capabilities,
            limitations=all_limitations,
        )

        # ── Step 8: Generate answer ───────────────────────────────────────────
        answer_text, mode = generate_answer(
            question=question,
            intent=intent,
            evidence_decision=evidence_decision,
            retrieval=retrieval,
            capabilities=capabilities,
            scope_allowed=True,
            is_injection=scope.is_injection,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # ── Step 9: Output validation ─────────────────────────────────────────
        validation = validate_output(
            answer=answer_text,
            intent=intent,
            evidence=retrieval.evidence,
            capabilities=capabilities,
            scope_allowed=True,
        )

        blocked = not validation.allowed
        if blocked:
            answer_text = (
                "I found related information, but I cannot safely return that answer "
                "based on the available evidence. Please refine your question."
            )
            mode = "blocked_out_of_scope"

        # Merge validation warnings into limitations
        final_limitations = all_limitations + validation.warnings

        # ── Step 10: Audit log ────────────────────────────────────────────────
        self._log(
            request=request,
            intent=intent,
            capabilities=capabilities,
            retrievers_used=retrieval.retrievers_used,
            evidence_count=len(retrieval.evidence),
            evidence_status=evidence_decision.status,
            response_mode=mode,
            blocked=blocked,
            block_reason=None if not blocked else validation.reason,
            warnings=validation.warnings,
            answer_text=answer_text,
            scope_allowed=True,
        )

        # ── Step 11: Build response ───────────────────────────────────────────
        trace: dict = {}
        if request.include_guardrail_trace:
            trace = self._build_trace(
                request, scope, intent, intent_decision,
                evidence_decision, mode, retrieval.retrievers_used,
                validation.warnings, capabilities,
            )

        return GuardedQueryResponse(
            allowed=not blocked,
            intent=intent,
            mode=mode,
            answer=answer_text,
            evidence_used=retrieval.evidence[:8],
            limitations=final_limitations,
            suggested_next_actions=_NEXT_ACTIONS.get(mode, []),
            guardrail_trace=trace,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _log(
        self,
        request: GuardedQueryRequest,
        intent: str,
        capabilities: dict,
        retrievers_used: list[str],
        evidence_count: int,
        evidence_status: str,
        response_mode: str,
        blocked: bool,
        block_reason: Optional[str],
        warnings: list[str],
        answer_text: str,
        scope_allowed: bool,
    ) -> None:
        try:
            log_guardrail_event(
                question=request.question,
                document_id=request.document_id,
                candidate_id=request.candidate_id,
                scope_allowed=scope_allowed,
                intent=intent,
                required_capabilities=INTENT_REQUIRED_CAPABILITIES.get(intent, []),
                available_capabilities=capabilities,
                retrievers_used=retrievers_used,
                evidence_count=evidence_count,
                evidence_status=evidence_status,
                response_mode=response_mode,
                blocked=blocked,
                block_reason=block_reason,
                warnings=warnings,
                answer_preview=answer_text,
            )
        except Exception as exc:
            logger.warning("Audit log failed (non-fatal): %s", exc)

    def _build_trace(
        self,
        request: GuardedQueryRequest,
        scope,
        intent: str,
        intent_decision,
        evidence_decision,
        mode: str,
        retrievers_used: list[str],
        output_warnings: list[str],
        capabilities: dict,
    ) -> dict:
        return {
            "scope_check": {
                "allowed": scope.allowed,
                "confidence": scope.confidence,
                "reason": scope.reason,
                "is_injection": scope.is_injection,
            },
            "intent": {
                "classified_as": intent,
                "confidence": getattr(intent_decision, "confidence", None),
                "reason": getattr(intent_decision, "reason", None),
                "required_capabilities": INTENT_REQUIRED_CAPABILITIES.get(intent, []),
            },
            "evidence": {
                "status": getattr(evidence_decision, "status", None),
                "reason": getattr(evidence_decision, "reason", None),
                "retrievers_used": retrievers_used,
            },
            "capabilities": {
                k: v for k, v in capabilities.items()
                if k != "audit_log"         # Don't expose internal log flag
            },
            "response_mode": mode,
            "output_validation_warnings": output_warnings,
        }
