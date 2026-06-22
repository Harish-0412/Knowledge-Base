from app.core.errors import AppError
from app.core.config import get_settings
from app.db.models import Document, DocumentProfile
from app.extractors.base import ExtractedBlock
from app.extractors.chandra_ocr_extractor import ChandraOCRExtractor
from app.extractors.csv_extractor import CSVExtractor
from app.extractors.docling_extractor import DoclingExtractor
from app.extractors.pymupdf_extractor import PyMuPDFExtractor
from app.extractors.text_extractor import TextExtractor


class ExtractionRouterService:
    def extract(self, document: Document, profiles: list[DocumentProfile]) -> tuple[list[ExtractedBlock], list[str]]:
        if not profiles:
            raise AppError(
                code="profile_required",
                message="Document profile is required before extraction.",
                status_code=400,
                details={"document_id": document.document_id},
            )

        blocks: list[ExtractedBlock] = []
        warnings: list[str] = []
        settings = get_settings()
        extractors_by_name = {
            "text": TextExtractor(),
            "csv": CSVExtractor(),
            "pymupdf": PyMuPDFExtractor(),
            "docling": DoclingExtractor(),
            "chandra_ocr": ChandraOCRExtractor(),
            "docling_disabled": DoclingExtractor(),
            "chandra_ocr_disabled": ChandraOCRExtractor(),
        }

        grouped_profiles: dict[str, list[DocumentProfile]] = {}
        for profile in profiles:
            grouped_profiles.setdefault(profile.recommended_extractor, []).append(profile)

        for extractor_name, extractor_profiles in grouped_profiles.items():
            extractor = extractors_by_name.get(extractor_name)
            if extractor is None:
                raise AppError(
                    code="unsupported_extractor",
                    message=f"Extractor '{extractor_name}' is not supported in Phase 4.",
                    status_code=400,
                    details={"extractor": extractor_name},
                )
            try:
                extracted = extractor.extract(document, extractor_profiles)
            except AppError as exc:
                fallback_name = self._fallback_extractor_name(extractor_name)
                if fallback_name is None or fallback_name == extractor_name:
                    raise
                fallback = extractors_by_name[fallback_name]
                warnings.append(
                    f"Extractor {extractor_name} failed with {exc.code}; fell back to {fallback_name}."
                )
                extracted = fallback.extract(document, extractor_profiles)
            selected_pages = {profile.page_number for profile in extractor_profiles}
            for block in extracted:
                if settings.debug_extractor_comparison:
                    block.metadata_json["comparison_mode"] = True
                elif selected_pages and block.page_number not in selected_pages:
                    continue
                block.metadata_json["extractor_selected_by_profile"] = extractor_name
                blocks.append(block)

        if not blocks:
            warnings.append("Extraction completed, but no content blocks were produced.")

        return blocks, warnings

    def _fallback_extractor_name(self, extractor_name: str) -> str | None:
        settings = get_settings()
        if not settings.pymupdf_fallback_enabled:
            return None
        if extractor_name in {"docling", "docling_disabled"}:
            return "pymupdf"
        if extractor_name in {"chandra_ocr", "chandra_ocr_disabled"}:
            return "pymupdf"
        return None
