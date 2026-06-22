from importlib.util import find_spec

from app.core.config import get_settings
from app.db.models import Document, DocumentProfile


class ProfilerService:
    def profile_document(self, document: Document) -> list[DocumentProfile]:
        if document.source_type in {"text", "markdown"}:
            return [self._profile_item(document.document_id, "text", "text", 0.95, "Plain text document")]

        if document.source_type == "csv":
            return [self._profile_item(document.document_id, "table", "csv", 0.95, "CSV compatibility matrix")]

        if document.source_type == "pdf":
            return self._profile_pdf(document)

        if document.source_type == "docx":
            return [self._profile_docx(document.document_id)]

        return [
            self._profile_item(
                document.document_id,
                "unknown",
                "unsupported",
                0.1,
                f"No profiler is available for source type {document.source_type}",
            )
        ]

    def _profile_pdf(self, document: Document) -> list[DocumentProfile]:
        try:
            import fitz  # type: ignore[import-not-found]
        except ImportError:
            return [
                self._profile_item(
                    document.document_id,
                    "pdf",
                    "pymupdf_unavailable",
                    0.2,
                    "PyMuPDF is not installed, so PDF pages could not be inspected.",
                    signals={"pymupdf_available": False},
                )
            ]

        profiles: list[DocumentProfile] = []
        with fitz.open(document.file_path) as pdf:
            for page_index, page in enumerate(pdf, start=1):
                text = page.get_text("text") or ""
                image_count = len(page.get_images(full=True))
                page_area = max(float(page.rect.width * page.rect.height), 1.0)
                selectable_text_length = len(text.strip())
                text_density = selectable_text_length / page_area
                table_hint_score = self._table_hint_score(text)
                scanned_score = 0.8 if selectable_text_length < 50 and image_count > 0 else 0.1
                layout_complexity_score = min(1.0, (text.count("\n") / 80) + (image_count * 0.1) + table_hint_score)

                extractor, confidence, reason, page_type = self._choose_pdf_extractor(
                    selectable_text_length=selectable_text_length,
                    image_count=image_count,
                    table_hint_score=table_hint_score,
                    text_density=text_density,
                    scanned_score=scanned_score,
                    layout_complexity_score=layout_complexity_score,
                )
                profiles.append(
                    self._profile_item(
                        document.document_id,
                        page_type,
                        extractor,
                        confidence,
                        reason,
                        page_number=page_index,
                        signals={
                            "selectable_text_length": selectable_text_length,
                            "embedded_text_length": selectable_text_length,
                            "image_count": image_count,
                            "has_tables_hint": table_hint_score > 0,
                            "table_hint_score": table_hint_score,
                            "scanned_score": scanned_score,
                            "layout_complexity_score": layout_complexity_score,
                            "text_density": text_density,
                            "pymupdf_available": True,
                        },
                    )
                )

        if not profiles:
            return [
                self._profile_item(
                    document.document_id,
                    "pdf",
                    "pymupdf",
                    0.3,
                    "PDF opened successfully but contained no pages.",
                    signals={"pymupdf_available": True},
                )
            ]
        return profiles

    def _profile_docx(self, document_id: str) -> DocumentProfile:
        settings = get_settings()
        if (settings.enable_docling or settings.docling_enabled) and find_spec("docling") is not None:
            return self._profile_item(document_id, "document", "docling", 0.75, "DOCX can be handled by Docling.")

        if not (settings.enable_docling or settings.docling_enabled):
            return self._profile_item(
                document_id,
                "document",
                "docling_disabled",
                0.35,
                "DOCX was stored, but Docling extraction is disabled.",
                signals={"docling_enabled": False},
            )

        return self._profile_item(
            document_id,
            "document",
            "unsupported_docx_placeholder",
            0.35,
            "DOCX was stored, but Docling is not installed yet.",
            signals={"docling_available": False},
        )

    def _choose_pdf_extractor(
        self,
        selectable_text_length: int,
        image_count: int,
        table_hint_score: float,
        text_density: float,
        scanned_score: float,
        layout_complexity_score: float,
    ) -> tuple[str, float, str, str]:
        settings = get_settings()
        if scanned_score >= 0.7:
            if not (settings.enable_chandra_ocr or settings.chandra_ocr_enabled) and not settings.use_mock_ocr:
                return "chandra_ocr_disabled", 0.35, "PDF appears scanned, but Chandra OCR is disabled.", "scanned_pdf"
            return "chandra_ocr", 0.75, "PDF page has very low selectable text and image content.", "scanned_pdf"

        if (settings.docling_enabled or settings.enable_docling) and settings.preferred_parser == "docling":
            return "docling", 0.78, "Docling is configured as the preferred PDF parser.", "structured_pdf"

        if table_hint_score >= 0.5 or layout_complexity_score >= 0.7:
            if not (settings.enable_docling or settings.docling_enabled):
                return "pymupdf", 0.65, "PDF has layout/table signals, but Docling is disabled; using PyMuPDF text.", "text_pdf"
            return "docling", 0.7, "PDF page appears to contain table or layout-heavy content.", "structured_pdf"

        if selectable_text_length >= 50:
            return "pymupdf", 0.85, "PDF page has enough selectable text for PyMuPDF extraction.", "text_pdf"

        return "pymupdf", 0.45, "PDF page has limited signals, but PyMuPDF is available.", "pdf"

    def _has_table_hint(self, text: str) -> bool:
        return self._table_hint_score(text) > 0

    def _table_hint_score(self, text: str) -> float:
        lowered = text.lower()
        score = 0.0
        table_words = ("compatibility matrix", "supported versions", "minimum version", "table", "required bios")
        if any(word in lowered for word in table_words):
            score += 0.5
        if text.count("|") >= 4 or text.count("\t") >= 4:
            score += 0.4
        if len(repeated_columns := [line for line in text.splitlines() if len(line.split()) >= 4]) >= 3:
            score += 0.2
        return min(score, 1.0)

    def _profile_item(
        self,
        document_id: str,
        page_type: str,
        recommended_extractor: str,
        confidence: float,
        reason: str,
        page_number: int = 1,
        signals: dict | None = None,
    ) -> DocumentProfile:
        return DocumentProfile(
            document_id=document_id,
            page_number=page_number,
            page_type=page_type,
            recommended_extractor=recommended_extractor,
            confidence=confidence,
            reason=reason,
            signals_json=signals or {},
        )
