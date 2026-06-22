from __future__ import annotations

import re


class ChunkQualityValidator:
    def rejection_reason(self, text: str, chunk_type: str) -> str | None:
        stripped = text.strip().strip("# ")
        if not stripped:
            return "empty"
        if re.fullmatch(r"v?\d+(?:\.\d+)+(?:\.x)?", stripped, re.IGNORECASE):
            return "version_only"
        if re.fullmatch(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", stripped):
            return "date_only"
        if re.fullmatch(r"\d+", stripped):
            return "page_number_only"
        if chunk_type != "document_metadata" and len(stripped.split()) <= 3 and not re.search(r"[.!?:|]", stripped):
            return "too_short_without_context"
        return None
