from app.core.errors import AppError
from app.db.models import Document, DocumentProfile
from app.extractors.base import ExtractedBlock


class PyMuPDFExtractor:
    def extract(self, document: Document, profiles: list[DocumentProfile]) -> list[ExtractedBlock]:
        try:
            import fitz  # type: ignore[import-not-found]
        except ImportError as exc:
            raise AppError(
                code="extractor_dependency_missing",
                message="PyMuPDF is required for pymupdf extraction but is not installed.",
                status_code=400,
                details={"extractor": "pymupdf"},
            ) from exc

        blocks: list[ExtractedBlock] = []
        with fitz.open(document.file_path) as pdf:
            for page_index, page in enumerate(pdf, start=1):
                text = (page.get_text("text") or "").strip()
                if not text:
                    continue
                blocks.append(
                    ExtractedBlock(
                        page_number=page_index,
                        block_type="page_text",
                        text=text,
                        extraction_method="pymupdf",
                        quality_score=0.85,
                        metadata_json={"page_index": page_index},
                    )
                )
        return blocks
