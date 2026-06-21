"""Shared grounded-prompt and structured-response helpers."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..validation.citation_builder import CitationBuilder


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
REQUIRED_FIELDS = ("root_cause", "impact", "recommendation", "prevention", "evidence_sources")


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM response did not contain a JSON object")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


class GroundedChain:
    template_name = "grounded_answer_prompt.txt"

    def __init__(self, llm_service: Any, template_name: str | None = None) -> None:
        self.llm_service = llm_service
        self.template_path = PROMPTS_DIR / (template_name or self.template_name)
        self.citation_builder = CitationBuilder()

    def build_prompt(self, question: str, evidence_package: dict[str, Any]) -> tuple[str, list[str]]:
        evidence, citations = self.citation_builder.format_evidence(evidence_package)
        template = self.template_path.read_text(encoding="utf-8")
        return template.format(evidence=evidence or "NO EVIDENCE RETRIEVED", question=question), citations

    @staticmethod
    def insufficient_response() -> dict[str, Any]:
        return {
            "root_cause": "Insufficient evidence",
            "impact": "Insufficient evidence",
            "recommendation": "Insufficient evidence",
            "prevention": "Insufficient evidence",
            "evidence_sources": [],
        }

    @staticmethod
    def _canonicalize_citations(parsed: dict[str, Any], citations: list[str]) -> None:
        """Normalize compact model citations only when the evidence ID is known."""
        by_id = {citation.rsplit(" ", 1)[-1]: citation for citation in citations}
        for field, value in list(parsed.items()):
            if not isinstance(value, str):
                continue
            normalized = value
            for evidence_id, canonical in by_id.items():
                normalized = normalized.replace(f"[{evidence_id}]", canonical)
            parsed[field] = normalized

        normalized_sources = []
        for source in parsed.get("evidence_sources", []):
            source_text = str(source)
            evidence_id = source_text.strip("[]")
            normalized_sources.append(by_id.get(evidence_id, source_text))
        parsed["evidence_sources"] = list(dict.fromkeys(normalized_sources))

    def _call(self, question: str, evidence_package: dict[str, Any]) -> dict[str, Any]:
        prompt, citations = self.build_prompt(question, evidence_package)
        if not citations:
            response = self.insufficient_response()
            response["generation_status"] = "ABSTAINED"
            response["latency_ms"] = 0.0
            response["error"] = "No evidence was retrieved"
            return response

        generated = self.llm_service.generate_response(prompt)
        if generated.get("status") != "PASS":
            response = self.insufficient_response()
            response["generation_status"] = "FAIL"
            response["latency_ms"] = generated.get("latency_ms", 0.0)
            response["error"] = generated.get("error") or "LLM generation failed"
            return response

        parsed = parse_json_response(str(generated.get("response", "")))
        for field in REQUIRED_FIELDS:
            parsed.setdefault(field, [] if field == "evidence_sources" else "")
        self._canonicalize_citations(parsed, citations)
        parsed["generation_status"] = "PASS"
        parsed["latency_ms"] = generated.get("latency_ms", 0.0)
        parsed["error"] = None
        return parsed
