import json
from pathlib import Path

from app.extractors.base import ExtractedBlock
from app.services.llm_context_pack_builder import LLMContextPackBuilder
from app.services.chunking_service import ChunkingService
from app.services.local_export_service import LocalExportService


def chunk_texts(text: str):
    service = ChunkingService()
    chunks = service.create_chunks(
        "DOC-TEST",
        [ExtractedBlock(page_number=1, block_type="page_text", text=text, extraction_method="pymupdf")],
    )
    return chunks, service


def test_metadata_grouping():
    chunks, _ = chunk_texts(
        """ACME ENTERPRISE COMPUTING
Platform Compatibility &amp; Firmware Release Notes
Document ID
ACME-RN-2026-06
Release Version
6.4.2
Release Date
15 June 2026
"""
    )

    metadata = [chunk for chunk in chunks if chunk.chunk_type == "document_metadata"]
    assert len(metadata) == 1
    assert "Document ID: ACME-RN-2026-06" in metadata[0].text
    assert "Release Version: 6.4.2" in metadata[0].text
    assert "Release Date: 15 June 2026" in metadata[0].text
    assert metadata[0].send_to_llm is False


def test_heading_and_paragraph_grouping():
    chunks, _ = chunk_texts(
        """## 1. Overview

ACME Platform Release 6.4.2 introduces firmware stability improvements.
"""
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "overview"
    assert chunks[0].section_title == "1. Overview"
    assert "ACME Platform Release" in chunks[0].text
    assert chunks[0].send_to_llm is False


def test_standalone_version_rejected():
    chunks, service = chunk_texts("6.4.2")

    assert chunks == []
    assert service.stats.rejected >= 1


def test_requirement_rule_detection():
    chunks, _ = chunk_texts("Windows 11 23H2 requires BIOS version 8.2.1 or later.")

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "minimum_version_requirement"
    assert chunks[0].semantic_zone == "compatibility_requirements"
    assert chunks[0].llm_usage == "rule_extraction"
    assert chunks[0].rule_likelihood == "high"
    assert chunks[0].send_to_llm is True


def test_unsupported_configuration_classification():
    chunks, _ = chunk_texts("Windows 10 21H2 is not supported with Secure Driver Pack 14.0.0 on ACME ProBook 440 G9.")

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "unsupported_configuration"
    assert chunks[0].semantic_zone == "unsupported_configurations"
    assert chunks[0].llm_usage == "rule_extraction"


def test_compound_rule_preservation():
    chunks, _ = chunk_texts(
        "VMware ESXi 5.1.x with QLogic QLE24xx HBA and Intel Xeon E5-2400 V2 processors "
        "requires BIOS 02.04.02 or later."
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "compound_requirement"
    assert "QLogic QLE24xx" in chunks[0].text
    assert chunks[0].send_to_llm is True


def test_table_row_with_headers():
    service = ChunkingService()
    chunks = service.create_chunks(
        "DOC-TEST",
        [
            ExtractedBlock(
                page_number=1,
                block_type="table_row",
                text="R420 ESXi 5.1.x 02.04.02 6.4.2",
                extraction_method="csv",
                metadata_json={
                    "headers": ["Model", "OS", "Required BIOS", "Required Firmware"],
                    "values": ["R420", "ESXi 5.1.x", "02.04.02", "6.4.2"],
                    "row_number": 1,
                },
            )
        ],
    )

    assert chunks[0].text == "Model: R420 | OS: ESXi 5.1.x | Required BIOS: 02.04.02 | Required Firmware: 6.4.2"
    assert chunks[0].chunk_type == "component_table_row"
    assert chunks[0].table_headers_json == ["Model", "OS", "Required BIOS", "Required Firmware"]
    assert chunks[0].table_row_json["Model"] == "R420"
    assert chunks[0].metadata_json["strategy"] == "table_row_with_headers"


def test_markdown_table_rows_become_independent_chunks():
    chunks, _ = chunk_texts(
        """## Supported Components

| Component | Version |
|----------------------|-----------|
| System BIOS | 6.4.2 |
| System Firmware | 8.2.1 |
| Platform Driver Pack | 12.5.0 |
| Security Agent | 4.8.3 |
"""
    )

    table_chunks = [chunk for chunk in chunks if chunk.chunk_type == "component_table_row"]

    assert len(table_chunks) == 4
    assert [chunk.text for chunk in table_chunks] == [
        "Component: System BIOS | Version: 6.4.2",
        "Component: System Firmware | Version: 8.2.1",
        "Component: Platform Driver Pack | Version: 12.5.0",
        "Component: Security Agent | Version: 4.8.3",
    ]
    assert len({chunk.source_excerpt for chunk in table_chunks}) == 4
    assert all(chunk.llm_usage == "rule_extraction" for chunk in table_chunks)
    assert all(chunk.metadata_json["strategy"] == "markdown_table_row_with_headers" for chunk in table_chunks)
    assert table_chunks[1].table_row_json == {"Component": "System Firmware", "Version": "8.2.1"}


def test_compliance_validation_table_produces_one_chunk_per_row():
    chunks, _ = chunk_texts(
        """## Compliance Validation Rules

| Component | Minimum Version | Current Release |
|---------------------------|---------|---------|
| BIOS | 6.4.2 | 6.4.2 |
| Firmware | 8.2.0 | 8.2.1 |
| Driver Pack | 12.5.0 | 12.5.0 |
| Security Agent | 4.8.3 | 4.8.3 |
| Endpoint Management Agent | 3.7.0 | 3.7.1 |
| Enterprise OS | 2025.2 | 2026.1 |
"""
    )

    table_chunks = [chunk for chunk in chunks if chunk.chunk_type == "component_table_row"]

    assert len(table_chunks) == 6
    assert table_chunks[1].text == "Component: Firmware | Minimum Version: 8.2.0 | Current Release: 8.2.1"
    assert table_chunks[4].text == (
        "Component: Endpoint Management Agent | Minimum Version: 3.7.0 | Current Release: 3.7.1"
    )


def test_duplicate_extractor_output_deduplicated():
    service = ChunkingService()
    chunks = service.create_chunks(
        "DOC-TEST",
        [
            ExtractedBlock(page_number=1, block_type="page_text", text="Windows requires BIOS 1.2.3 or later.", extraction_method="pymupdf"),
            ExtractedBlock(page_number=1, block_type="layout_text", text="Windows requires BIOS 1.2.3 or later.", extraction_method="docling"),
        ],
    )

    assert len(chunks) == 1
    assert chunks[0].extraction_method == "docling"
    assert service.stats.deduplicated == 1


def test_llm_usage_classification():
    chunks, _ = chunk_texts(
        """Document ID
ACME-RN-2026-06

## 1. Overview
ACME Platform Release 6.4.2 introduces firmware stability improvements.

Windows 11 23H2 requires BIOS version 8.2.1 or later.
"""
    )

    usage = {chunk.chunk_type: chunk.llm_usage for chunk in chunks}
    assert usage["document_metadata"] == "global_context"
    assert usage["overview"] == "background_context"
    assert usage["minimum_version_requirement"] == "rule_extraction"


def test_llm_input_and_csv_exports(tmp_path: Path):
    chunks, _ = chunk_texts(
        """Document ID
ACME-RN-2026-06

Windows 11 23H2 requires BIOS version 8.2.1 or later.
"""
    )

    paths = LocalExportService(str(tmp_path)).write_chunks("DOC-TEST", chunks)
    llm_payload = json.loads(Path(paths["llm_input_chunks"]).read_text(encoding="utf-8"))
    csv_text = Path(paths["chunks_csv"]).read_text(encoding="utf-8")

    assert llm_payload["chunks"]
    assert all(chunk["send_to_llm"] for chunk in llm_payload["chunks"])
    assert "text" in csv_text
    assert "source_excerpt" in csv_text
    assert "semantic_zone" in csv_text
    assert "llm_usage" in csv_text
    assert "section_path" in csv_text
    assert "rule_signals" in csv_text


def test_llm_context_pack_excludes_metadata_from_rule_chunks():
    chunks, _ = chunk_texts(
        """Document ID
ACME-RN-2026-06

Windows 11 23H2 requires BIOS version 8.2.1 or later.
"""
    )

    pack = LLMContextPackBuilder().build("DOC-TEST", chunks)

    assert pack["document_context"]
    assert pack["global_context_chunks"]
    assert pack["rule_extraction_chunks"]
    assert all(chunk["chunk_type"] != "document_metadata" for chunk in pack["rule_extraction_chunks"])
