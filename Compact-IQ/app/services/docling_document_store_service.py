from __future__ import annotations

from typing import Any

from app.services.local_export_service import LocalExportService


class DoclingDocumentStoreService:
    def __init__(self, export_service: LocalExportService | None = None) -> None:
        self.export_service = export_service or LocalExportService()

    def save_debug_exports(
        self,
        document_id: str,
        *,
        document_json: Any | None = None,
        markdown: str | None = None,
        hybrid_chunks: list[dict] | None = None,
    ) -> dict[str, str]:
        paths: dict[str, str] = {}
        if document_json is not None:
            paths["docling_document"] = self.export_service.write(document_id, "docling_document", document_json)
        if markdown is not None:
            path = self.export_service.export_path(document_id, "docling_markdown")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown, encoding="utf-8")
            paths["docling_markdown"] = str(path)
        if hybrid_chunks is not None:
            paths["docling_hybrid_chunks"] = self.export_service.write(document_id, "docling_hybrid_chunks", hybrid_chunks)
        return paths
