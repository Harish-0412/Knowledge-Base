from pathlib import Path
from typing import Any

from app.core.errors import AppError
from app.db.models import Document, DocumentProfile
from app.extractors.base import ExtractedBlock
from app.services.docling_document_store_service import DoclingDocumentStoreService
from app.services.docling_hybrid_chunker_service import DoclingHybridChunkerService
from app.services.docling_parser_service import DoclingParserService


class DoclingExtractor:
    def extract(self, document: Document, profiles: list[DocumentProfile]) -> list[ExtractedBlock]:
        try:
            result = DoclingParserService().parse(document.file_path)
        except Exception as exc:
            if isinstance(exc, AppError):
                raise
            raise AppError(
                code="extractor_failed",
                message="Docling extraction failed.",
                status_code=400,
                details={"extractor": "docling", "error": exc.__class__.__name__},
            ) from exc

        blocks = self._blocks_from_docling_result(document, result)
        if not blocks:
            raise AppError(
                code="extractor_empty_output",
                message="Docling extraction completed but produced no text blocks.",
                status_code=400,
                details={"extractor": "docling"},
            )
        return blocks

    def _blocks_from_docling_result(self, document: Document, result: Any) -> list[ExtractedBlock]:
        docling_document = getattr(result, "document", result)
        markdown = self._export_markdown(docling_document)
        docling_json = self._export_json(docling_document)
        hybrid_chunks, hybrid_warnings = DoclingHybridChunkerService().chunk(docling_document, fallback_text=markdown)
        DoclingDocumentStoreService().save_debug_exports(
            document.document_id,
            document_json=docling_json,
            markdown=markdown or None,
            hybrid_chunks=hybrid_chunks,
        )
        if markdown:
            return [
                ExtractedBlock(
                    page_number=1,
                    block_type="layout_text",
                    text=markdown,
                    extraction_method="docling",
                    section_title=Path(document.original_filename).stem,
                    quality_score=0.85,
                    metadata_json={
                        "format": "markdown",
                        "layout_aware": True,
                        "source_parser": "docling",
                        "source_chunker": "docling_hybrid_chunker",
                        "hybrid_chunk_count": len(hybrid_chunks),
                        "hybrid_warnings": hybrid_warnings,
                    },
                )
            ]

        text = self._export_text(docling_document)
        if text:
            return [
                ExtractedBlock(
                    page_number=1,
                    block_type="layout_text",
                    text=text,
                    extraction_method="docling",
                    section_title=Path(document.original_filename).stem,
                    quality_score=0.75,
                    metadata_json={
                        "format": "text",
                        "layout_aware": True,
                        "source_parser": "docling",
                        "source_chunker": "docling_hybrid_chunker",
                        "hybrid_chunk_count": len(hybrid_chunks),
                        "hybrid_warnings": hybrid_warnings,
                    },
                )
            ]
        return []

    def _export_markdown(self, docling_document: Any) -> str:
        for method_name in ("export_to_markdown", "export_to_markdown_str"):
            method = getattr(docling_document, method_name, None)
            if callable(method):
                return str(method()).strip()
        return ""

    def _export_text(self, docling_document: Any) -> str:
        for method_name in ("export_to_text", "export_to_text_str"):
            method = getattr(docling_document, method_name, None)
            if callable(method):
                return str(method()).strip()
        return str(docling_document).strip() if docling_document is not None else ""

    def _export_json(self, docling_document: Any) -> Any:
        for method_name in ("export_to_dict", "export_to_json"):
            method = getattr(docling_document, method_name, None)
            if callable(method):
                try:
                    return method()
                except Exception:
                    continue
        return {"repr": repr(docling_document)[:2000]}
