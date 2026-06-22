from pathlib import Path

import httpx
import pytest

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import Document, DocumentProfile
from app.extractors.chandra_ocr_extractor import ChandraOCRExtractor
from app.extractors.docling_extractor import DoclingExtractor


def make_document(tmp_path: Path, filename: str = "sample.pdf") -> Document:
    file_path = tmp_path / filename
    file_path.write_bytes(b"fake pdf")
    return Document(
        document_id="DOC-TEST",
        filename=filename,
        original_filename=filename,
        file_path=str(file_path),
        content_type="application/pdf",
        source_type="pdf",
        file_size_bytes=file_path.stat().st_size,
        status="uploaded",
        metadata_json={},
    )


def make_profile(extractor: str = "docling") -> DocumentProfile:
    return DocumentProfile(
        document_id="DOC-TEST",
        page_number=1,
        page_type="structured_pdf",
        recommended_extractor=extractor,
        confidence=0.8,
        reason="test",
        signals_json={},
    )


def test_docling_disabled_returns_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_DOCLING", "false")
    monkeypatch.setenv("DOCLING_ENABLED", "false")
    get_settings.cache_clear()

    with pytest.raises(AppError) as exc_info:
        DoclingExtractor().extract(make_document(tmp_path), [make_profile()])

    assert exc_info.value.code == "extractor_disabled"
    get_settings.cache_clear()


def test_docling_enabled_with_mocked_converter_returns_layout_text(tmp_path, monkeypatch):
    class FakeDoclingDocument:
        def export_to_markdown(self):
            return "# Heading\n\n| Component | Version |\n| BIOS | 2.0.21 |"

    class FakeResult:
        document = FakeDoclingDocument()

    monkeypatch.setenv("ENABLE_DOCLING", "true")
    monkeypatch.setattr("app.services.docling_parser_service.find_spec", lambda name: object())
    monkeypatch.setattr("app.services.docling_parser_service.DoclingParserService.parse", lambda self, file_path: FakeResult())
    get_settings.cache_clear()

    blocks = DoclingExtractor().extract(make_document(tmp_path), [make_profile()])

    assert len(blocks) == 1
    assert blocks[0].extraction_method == "docling"
    assert blocks[0].block_type == "layout_text"
    assert "| Component | Version |" in blocks[0].text
    assert blocks[0].metadata_json["layout_aware"] is True
    get_settings.cache_clear()


def test_chandra_disabled_returns_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_CHANDRA_OCR", "false")
    monkeypatch.setenv("USE_MOCK_OCR", "false")
    get_settings.cache_clear()

    with pytest.raises(AppError) as exc_info:
        ChandraOCRExtractor().extract(make_document(tmp_path), [make_profile("chandra_ocr")])

    assert exc_info.value.code == "extractor_disabled"
    get_settings.cache_clear()


def test_chandra_enabled_with_mocked_api_returns_ocr_blocks(tmp_path, monkeypatch):
    def fake_post(url, json, timeout):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "pages": [
                    {
                        "page_number": 1,
                        "text": "Scanned PDF requires BIOS 2.0.21 or later.",
                        "confidence": 0.91,
                    }
                ]
            },
        )

    monkeypatch.setenv("ENABLE_CHANDRA_OCR", "true")
    monkeypatch.setenv("USE_MOCK_OCR", "false")
    monkeypatch.setenv("CHANDRA_API_URL", "https://ocr.example.test/extract")
    monkeypatch.setattr("app.extractors.chandra_ocr_extractor.httpx.post", fake_post)
    get_settings.cache_clear()

    blocks = ChandraOCRExtractor().extract(make_document(tmp_path), [make_profile("chandra_ocr")])

    assert len(blocks) == 1
    assert blocks[0].extraction_method == "chandra_ocr"
    assert blocks[0].block_type == "ocr_text"
    assert blocks[0].quality_score == 0.91
    assert "BIOS 2.0.21" in blocks[0].text
    get_settings.cache_clear()
