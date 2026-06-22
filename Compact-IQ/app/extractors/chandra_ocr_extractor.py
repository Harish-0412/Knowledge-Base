import base64
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import Document, DocumentProfile
from app.extractors.base import ExtractedBlock


class ChandraOCRExtractor:
    def extract(self, document: Document, profiles: list[DocumentProfile]) -> list[ExtractedBlock]:
        settings = get_settings()
        if settings.use_mock_ocr:
            return [
                ExtractedBlock(
                    page_number=profile.page_number,
                    block_type="ocr_placeholder",
                    text="Mock OCR output is enabled, but no real OCR engine was called.",
                    extraction_method="chandra_ocr_mock",
                    quality_score=0.2,
                    metadata_json={"mock": True},
                )
                for profile in profiles
            ]

        if not settings.enable_chandra_ocr:
            raise AppError(
                code="extractor_disabled",
                message="Chandra OCR extraction is disabled. Set ENABLE_CHANDRA_OCR=true to enable it.",
                status_code=400,
                details={"extractor": "chandra_ocr"},
            )
        if not settings.chandra_api_url:
            raise AppError(
                code="extractor_not_configured",
                message="Chandra OCR is enabled but CHANDRA_API_URL is not configured.",
                status_code=400,
                details={"extractor": "chandra_ocr"},
            )

        payload = {
            "filename": document.original_filename,
            "content_base64": base64.b64encode(Path(document.file_path).read_bytes()).decode("ascii"),
            "pages": [profile.page_number for profile in profiles],
        }
        try:
            response = httpx.post(settings.chandra_api_url, json=payload, timeout=settings.chandra_timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise AppError(
                code="extractor_timeout",
                message="Chandra OCR request timed out.",
                status_code=400,
                details={"extractor": "chandra_ocr"},
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                code="extractor_failed",
                message="Chandra OCR request failed.",
                status_code=400,
                details={"extractor": "chandra_ocr", "error": exc.__class__.__name__},
            ) from exc
        except ValueError as exc:
            raise AppError(
                code="extractor_invalid_response",
                message="Chandra OCR returned invalid JSON.",
                status_code=400,
                details={"extractor": "chandra_ocr"},
            ) from exc

        return self._blocks_from_response(data)

    def _blocks_from_response(self, data: dict) -> list[ExtractedBlock]:
        pages = data.get("pages", [])
        blocks: list[ExtractedBlock] = []
        for page in pages:
            text = str(page.get("text", "")).strip()
            if not text:
                continue
            confidence = page.get("confidence", 0.5)
            try:
                quality_score = float(confidence)
            except (TypeError, ValueError):
                quality_score = 0.5
            blocks.append(
                ExtractedBlock(
                    page_number=int(page.get("page_number", 1)),
                    block_type="ocr_text",
                    text=text,
                    extraction_method="chandra_ocr",
                    quality_score=max(0.0, min(quality_score, 1.0)),
                    metadata_json={"ocr_confidence": confidence},
                )
            )
        if not blocks:
            raise AppError(
                code="extractor_empty_output",
                message="Chandra OCR completed but returned no text.",
                status_code=400,
                details={"extractor": "chandra_ocr"},
            )
        return blocks
