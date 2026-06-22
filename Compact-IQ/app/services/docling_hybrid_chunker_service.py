from __future__ import annotations

from typing import Any


class DoclingHybridChunkerService:
    def chunk(self, docling_document: Any, fallback_text: str = "") -> tuple[list[dict], list[str]]:
        warnings: list[str] = []
        try:
            from docling.chunking import HybridChunker  # type: ignore[import-not-found]
        except Exception:
            if fallback_text:
                return [{"text": fallback_text, "metadata": {"fallback": "hybrid_chunker_unavailable"}}], [
                    "Docling HybridChunker is unavailable; using exported document text as one structural chunk."
                ]
            return [], ["Docling HybridChunker is unavailable."]

        try:
            chunker = HybridChunker()
            chunks = []
            for index, chunk in enumerate(chunker.chunk(docling_document), start=1):
                text = getattr(chunk, "text", None) or str(chunk)
                chunks.append(
                    {
                        "chunk_index": index,
                        "text": text,
                        "metadata": self._safe_metadata(chunk),
                    }
                )
            return chunks, warnings
        except Exception as exc:
            warnings.append(f"Docling HybridChunker failed: {exc.__class__.__name__}")
            return ([{"text": fallback_text, "metadata": {"fallback": "hybrid_chunker_failed"}}] if fallback_text else []), warnings

    def _safe_metadata(self, chunk: Any) -> dict:
        meta = getattr(chunk, "meta", None) or getattr(chunk, "metadata", None)
        if isinstance(meta, dict):
            return meta
        return {"repr": repr(meta)[:500]} if meta is not None else {}
