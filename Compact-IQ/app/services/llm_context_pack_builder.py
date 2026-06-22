from __future__ import annotations

import re
from typing import Any

from app.db.models import DocumentChunk


class LLMContextPackBuilder:
    def build(self, document_id: str, chunks: list[DocumentChunk]) -> dict[str, Any]:
        global_chunks = [chunk for chunk in chunks if chunk.llm_usage == "global_context"]
        background_chunks = [chunk for chunk in chunks if chunk.llm_usage == "background_context"]
        rule_chunks = [chunk for chunk in chunks if chunk.llm_usage == "rule_extraction"]
        evidence_chunks = [chunk for chunk in chunks if chunk.llm_usage == "evidence_only"]
        return {
            "document_id": document_id,
            "document_context": self._document_context(global_chunks),
            "global_context_chunks": [self._chunk_payload(chunk) for chunk in global_chunks],
            "background_context_chunks": [self._chunk_payload(chunk) for chunk in background_chunks],
            "rule_extraction_chunks": [self._chunk_payload(chunk) for chunk in rule_chunks],
            "evidence_chunks": [self._chunk_payload(chunk) for chunk in evidence_chunks],
        }

    def _document_context(self, chunks: list[DocumentChunk]) -> dict[str, Any]:
        text = "\n".join(chunk.text for chunk in chunks)
        context = {
            "title": chunks[0].section_title if chunks else None,
            "document_id": self._field(text, "Document ID"),
            "release_version": self._field(text, "Release Version") or self._field(text, "Version"),
            "release_date": self._field(text, "Release Date") or self._field(text, "Published Date"),
            "applies_to": [],
        }
        applies_to = self._field(text, "Applies to")
        if applies_to:
            context["applies_to"] = [item.strip() for item in applies_to.split("|") if item.strip()]
        return context

    def _field(self, text: str, label: str) -> str | None:
        match = re.search(rf"^{re.escape(label)}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else None

    def _chunk_payload(self, chunk: DocumentChunk) -> dict[str, Any]:
        return {
            "chunk_id": chunk.chunk_id,
            "page_number": chunk.page_number,
            "section_path": chunk.section_path_json or [],
            "section_title": chunk.section_title,
            "semantic_zone": chunk.semantic_zone,
            "chunk_type": chunk.chunk_type,
            "source_excerpt": chunk.source_excerpt,
            "text": chunk.text,
            "extraction_method": chunk.extraction_method,
            "rule_signal_score": chunk.rule_signal_score,
            "rule_signals": chunk.rule_signals_json or [],
        }
