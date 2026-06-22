from __future__ import annotations

from importlib.util import find_spec
from typing import Any

from app.core.config import get_settings
from app.core.errors import AppError


class DoclingParserService:
    def parse(self, file_path: str) -> Any:
        settings = get_settings()
        if not (settings.docling_enabled or settings.enable_docling):
            raise AppError(
                code="extractor_disabled",
                message="Docling extraction is disabled. Set DOCLING_ENABLED=true or ENABLE_DOCLING=true to enable it.",
                status_code=400,
                details={"extractor": "docling"},
            )
        if find_spec("docling") is None:
            raise AppError(
                code="extractor_dependency_missing",
                message="Docling extraction was selected, but docling is not installed.",
                status_code=400,
                details={"extractor": "docling"},
            )

        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]

        converter = DocumentConverter()
        return converter.convert(file_path)
