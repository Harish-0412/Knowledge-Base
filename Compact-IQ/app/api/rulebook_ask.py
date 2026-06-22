"""
Compatibility Rulebook Ask Endpoint
POST /api/ask — answers a direct compatibility question using the llama assistant model.
Returns only the answer, no metadata or explanation wrappers.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.llm_service import LLMServiceFactory

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Rulebook"])

# Blocked categories (medical/financial)
_BLOCKED_KEYWORDS = [
    "medical", "health", "doctor", "hospital", "medicine", "treatment",
    "financial", "money", "bank", "loan", "credit", "investment", "stock",
    "insurance", "tax", "finance"
]

# Allowed categories: greetings, computer/IT, CompatIQ project
_ALLOWED_KEYWORDS = [
    # Greetings
    "hello", "hi", "hey", "how are you", "good morning", "good afternoon",
    "good evening", "good day", "nice to meet you", "what's up",
    # Computer/IT
    "computer", "it", "bios", "cpu", "ram", "motherboard", "hard drive",
    "ssd", "gpu", "operating system", "os", "windows", "linux", "mac",
    "software", "hardware", "network", "server", "internet", "wifi",
    "bluetooth", "usb", "driver", "update", "install", "download",
    "error", "bug", "fix", "troubleshoot", "laptop", "desktop",
    "keyboard", "mouse", "monitor", "printer", "scanner", "router",
    "modem", "firewall", "antivirus", "malware", "virus", "backup",
    # CompatIQ project
    "compatibility", "compat", "document", "upload", "rule", "candidate",
    "inventory", "device", "compliance", "analysis", "pipeline", "cisco",
    "knowledge base", "knowledgebase", "guardrail", "audit", "tier", "extract",
    "normalize", "review", "approve", "reject", "cve", "security", "release notes",
    "compatiq", "dashboard", "landing", "workspace", "profile", "chunk", "api"
]

_SYSTEM_PROMPT = (
    "You are a helpful CompatIQ assistant. "
    "You can answer greetings, CompatIQ project-related questions, and computer/IT related questions. "
    "You MUST NOT answer medical or financial questions. "
    "Answer ONLY in one short sentence. "
    "Give only the direct, correct answer — no preamble, no 'I think', no extra commentary, no paragraphs. "
    "If the question is medical or financial, or you don't know the answer, say 'I can only answer greetings, CompatIQ project questions, and computer/IT related questions. I cannot answer medical or financial questions.'."
)


class RulebookAskRequest(BaseModel):
    question: str


class RulebookAskResponse(BaseModel):
    answer: str


def is_allowed_question(question: str) -> bool:
    """Check if a question is allowed using keyword matching."""
    lower_question = question.lower()
    
    # Check if any blocked keyword is present
    if any(keyword in lower_question for keyword in _BLOCKED_KEYWORDS):
        return False
    
    # Check if any allowed keyword is present
    return any(keyword in lower_question for keyword in _ALLOWED_KEYWORDS)


@router.post("/ask", response_model=RulebookAskResponse)
def rulebook_ask(payload: RulebookAskRequest) -> RulebookAskResponse:
    """Answer a compatibility question using the llama assistant model.

    Uses assistant_ollama_model (llama3.2:3b by default).
    Returns only the direct answer — no citations, no chain-of-thought.
    """
    question = payload.question.strip()
    if not question:
        return RulebookAskResponse(answer="Please enter a question.")

    # Backend guardrails check
    if not is_allowed_question(question):
        return RulebookAskResponse(
            answer="I can only answer greetings, CompatIQ project questions, and computer/IT related questions. I cannot answer medical or financial questions."
        )

    settings = get_settings()

    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Question: {question}\n\n"
        "Answer (one short sentence only):"
    )

    try:
        llm = LLMServiceFactory.create(settings)
        raw = llm.generate_text(
            prompt,
            model=settings.assistant_ollama_model,
            options={"temperature": 0.0},
        )
        # Strip any leading labels the model may emit (e.g. "Answer: ...")
        answer = raw.strip()
        for prefix in ("Answer:", "answer:", "A:", "a:"):
            if answer.startswith(prefix):
                answer = answer[len(prefix):].strip()
                break
        # Ensure answer is not empty
        if not answer:
            answer = "I don't have enough information to answer that."
        return RulebookAskResponse(answer=answer)
    except Exception as exc:
        logger.warning("Rulebook ask LLM call failed: %s", exc)
        return RulebookAskResponse(
            answer="The compatibility assistant is currently unavailable. Please try again later."
        )
