import json
import csv
from pathlib import Path
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.core.config import get_settings


class LocalExportService:
    """Writes development/debug JSON exports. PostgreSQL remains the source of truth."""

    EXPORT_FILENAMES = {
        "profile": "profile.json",
        "docling_document": "docling_document.json",
        "docling_markdown": "docling_markdown.md",
        "docling_hybrid_chunks": "docling_hybrid_chunks.json",
        "document_blocks": "document_blocks.json",
        "document_sections": "document_sections.json",
        "chunks": "chunks.json",
        "chunks_csv": "chunks.csv",
        "llm_context_pack": "llm_context_pack.json",
        "llm_input_chunks": "llm_input_chunks.json",
        "document_objects": "document_objects.json",
        "processing_lane_report": "processing_lane_report.json",
        "deterministic_candidates": "deterministic_candidates.json",
        "llm_sections": "llm_sections.json",
        "llm_call_log": "llm_call_log.json",
        "raw_rule_candidates": "raw_rule_candidates.json",
        "normalized_rule_candidates": "normalized_rule_candidates.json",
        "candidate_quality_report": "candidate_quality_report.json",
        "normalization_warnings": "normalization_warnings.json",
        "pipeline_summary": "pipeline_summary.json",
    }

    def __init__(self, export_dir: str | None = None) -> None:
        self.export_root = Path(export_dir or get_settings().export_dir)

    def export_path(self, document_id: str, export_name: str) -> Path:
        filename = self.EXPORT_FILENAMES[export_name]
        return self.export_root / document_id / filename

    def write(self, document_id: str, export_name: str, payload: Any) -> str:
        path = self.export_path(document_id, export_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(jsonable_encoder(payload), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return str(path)

    def write_chunks(self, document_id: str, chunks: list[Any]) -> dict[str, str]:
        self.ensure_docling_placeholders(document_id)
        payload = {
            "document_id": document_id,
            "chunks": [self._chunk_payload(chunk) for chunk in chunks],
        }
        llm_payload = {
            "document_id": document_id,
            "chunks": [item for item in payload["chunks"] if item["send_to_llm"]],
        }
        json_path = self.write(document_id, "chunks", payload)
        llm_path = self.write(document_id, "llm_input_chunks", llm_payload)
        csv_path = self._write_chunks_csv(document_id, payload["chunks"])
        block_path = self.write(document_id, "document_blocks", self._blocks_payload(document_id, payload["chunks"]))
        section_path = self.write(document_id, "document_sections", self._sections_payload(document_id, payload["chunks"]))
        return {
            "chunks": json_path,
            "chunks_csv": csv_path,
            "llm_input_chunks": llm_path,
            "document_blocks": block_path,
            "document_sections": section_path,
        }

    def ensure_docling_placeholders(self, document_id: str) -> None:
        if not self.export_path(document_id, "docling_document").exists():
            self.write(
                document_id,
                "docling_document",
                {"available": False, "warning": "Docling document export was not produced for this run."},
            )
        markdown_path = self.export_path(document_id, "docling_markdown")
        if not markdown_path.exists():
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text("Docling markdown export was not produced for this run.\n", encoding="utf-8")
        if not self.export_path(document_id, "docling_hybrid_chunks").exists():
            self.write(
                document_id,
                "docling_hybrid_chunks",
                {
                    "available": False,
                    "chunks": [],
                    "warning": "Docling HybridChunker output was not produced for this run.",
                },
            )

    def _write_chunks_csv(self, document_id: str, rows: list[dict]) -> str:
        path = self.export_path(document_id, "chunks_csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "chunk_id",
            "document_id",
            "page_number",
            "chunk_index",
            "chunk_type",
            "section_title",
            "section_path",
            "text",
            "source_excerpt",
            "source_parser",
            "source_chunker",
            "extraction_method",
            "quality_score",
            "semantic_zone",
            "semantic_zone_confidence",
            "llm_usage",
            "rule_signal_score",
            "rule_signals",
            "rule_likelihood",
            "send_to_llm",
            "character_count",
            "token_estimate",
            "deduplication_status",
            "metadata_json",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                csv_row = {field: row.get(field) for field in fieldnames}
                csv_row["section_path"] = json.dumps(row.get("section_path_json") or [])
                csv_row["rule_signals"] = json.dumps(row.get("rule_signals_json") or [])
                csv_row["metadata_json"] = json.dumps(row.get("metadata_json") or {}, sort_keys=True)
                writer.writerow(csv_row)
        return str(path)

    def _chunk_payload(self, chunk: Any) -> dict:
        return {
            "chunk_id": getattr(chunk, "chunk_id", None),
            "document_id": getattr(chunk, "document_id", None),
            "page_number": getattr(chunk, "page_number", None),
            "chunk_index": getattr(chunk, "chunk_index", None),
            "chunk_type": getattr(chunk, "chunk_type", None),
            "section_title": getattr(chunk, "section_title", None),
            "text": getattr(chunk, "text", ""),
            "source_excerpt": getattr(chunk, "source_excerpt", ""),
            "source_parser": getattr(chunk, "source_parser", None),
            "source_chunker": getattr(chunk, "source_chunker", None),
            "extraction_method": getattr(chunk, "extraction_method", None),
            "quality_score": getattr(chunk, "quality_score", None),
            "section_path_json": getattr(chunk, "section_path_json", None),
            "semantic_zone": getattr(chunk, "semantic_zone", None),
            "semantic_zone_confidence": getattr(chunk, "semantic_zone_confidence", None),
            "classification_signals_json": getattr(chunk, "classification_signals_json", None),
            "llm_usage": getattr(chunk, "llm_usage", "ignore"),
            "rule_signal_score": getattr(chunk, "rule_signal_score", 0),
            "rule_signals_json": getattr(chunk, "rule_signals_json", None),
            "rule_likelihood": getattr(chunk, "rule_likelihood", "low"),
            "send_to_llm": getattr(chunk, "send_to_llm", False),
            "table_headers_json": getattr(chunk, "table_headers_json", None),
            "table_row_json": getattr(chunk, "table_row_json", None),
            "character_count": getattr(chunk, "character_count", 0),
            "token_estimate": getattr(chunk, "token_estimate", 0),
            "deduplication_status": getattr(chunk, "deduplication_status", "kept"),
            "metadata_json": getattr(chunk, "metadata_json", {}),
        }

    def _blocks_payload(self, document_id: str, chunks: list[dict]) -> dict:
        return {
            "document_id": document_id,
            "blocks": [
                {
                    "block_id": f"B-{index + 1:03d}",
                    "document_id": document_id,
                    "page_number": chunk["page_number"],
                    "block_index": index,
                    "block_type": chunk["chunk_type"],
                    "text": chunk["text"],
                    "source_parser": chunk["source_parser"],
                    "source_extractor": chunk["extraction_method"],
                    "section_hint": chunk["section_title"],
                    "metadata": chunk["metadata_json"],
                }
                for index, chunk in enumerate(chunks)
            ],
        }

    def _sections_payload(self, document_id: str, chunks: list[dict]) -> dict:
        grouped: dict[str, list[dict]] = {}
        for chunk in chunks:
            key = chunk["section_title"] or chunk["semantic_zone"] or "Document"
            grouped.setdefault(key, []).append(chunk)
        return {
            "document_id": document_id,
            "sections": [
                {
                    "section_id": f"SEC-{index + 1:03d}",
                    "section_title": title,
                    "section_path": group[0].get("section_path_json") or ([title] if title else []),
                    "page_start": min(item["page_number"] for item in group),
                    "page_end": max(item["page_number"] for item in group),
                    "semantic_zone": group[0].get("semantic_zone"),
                    "semantic_zone_confidence": group[0].get("semantic_zone_confidence"),
                    "classification_signals": group[0].get("classification_signals_json") or [],
                    "chunk_ids": [item["chunk_id"] for item in group],
                }
                for index, (title, group) in enumerate(grouped.items())
            ],
        }

    def export_status(self, document_id: str) -> dict:
        status = {}
        for export_name in self.EXPORT_FILENAMES:
            path = self.export_path(document_id, export_name)
            status[export_name] = {
                "path": str(path),
                "exists": path.exists(),
            }
        return status
