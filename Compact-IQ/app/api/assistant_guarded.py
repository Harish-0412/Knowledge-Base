"""
CompatIQ Guarded Assistant API Router
Exposes POST /api/assistant/guarded-query and leaves existing /api/assistant/query untouched.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.guardrails.schemas import GuardedQueryRequest, GuardedQueryResponse
from app.guardrails.service import GuardrailService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/assistant",
    tags=["Assistant"],
)


@router.post(
    "/guarded-query",
    response_model=GuardedQueryResponse,
    summary="Guarded assistant query",
    description=(
        "Production-style guardrail pipeline. Checks domain scope, classifies intent, "
        "retrieves Document Intelligence evidence, validates output, and returns a "
        "structured, grounded answer. Blocks out-of-scope and unsafe questions. "
        "Returns capability_missing for questions requiring KG/inventory/compliance "
        "subsystems that are not yet connected."
    ),
)
def guarded_query(
    request: GuardedQueryRequest,
    db: Session = Depends(get_db),
) -> GuardedQueryResponse:
    """Run a user question through the full CompatIQ guardrail pipeline."""
    service = GuardrailService(db)
    return service.answer(request)


@router.post(
    "/query",
    summary="Legacy assistant query (pass-through to guardrail)",
    description=(
        "Legacy endpoint. Now routes through the guardrail pipeline. "
        "Returns a simplified response compatible with the old frontend."
    ),
)
def legacy_query(request: dict, db: Session = Depends(get_db)) -> dict:
    """Legacy /api/assistant/query endpoint — routes through guardrail service.

    Accepts {question: str} and returns {response: str} for backward compatibility
    with the existing frontend chat implementation.
    """
    question = request.get("question", "").strip()
    if not question:
        return {"response": "Please enter a question.", "mode": "error"}

    guarded_req = GuardedQueryRequest(
        question=question,
        include_guardrail_trace=False,
    )
    try:
        result = GuardrailService(db).answer(guarded_req)
        return {
            "response": result.answer,
            "mode": result.mode,
            "intent": result.intent,
            "allowed": result.allowed,
        }
    except Exception as exc:
        logger.error("Legacy assistant query failed: %s", exc)
        return {
            "response": "The assistant encountered an internal error. Please try again.",
            "mode": "error",
        }
