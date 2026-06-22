from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.db.models import DocumentChunk
from app.extractors.base import ExtractedBlock
from app.services.rule_signal_scorer import RuleSignalScorer


RULE_KEYWORDS = (
    "requires",
    "required",
    "minimum",
    "at least",
    "or later",
    "must",
    "must not",
    "should not",
    "not supported",
    "unsupported",
    "incompatible",
    "only supported",
    "certified with",
    "depends on",
    "before upgrading",
    "after upgrading",
    "corrected an issue",
    "fixed an issue",
    "added support",
    "back-flashing",
    "downgrade",
    "firmware",
    "bios",
    "driver",
    "os",
    "agent",
)

METADATA_LABELS = {
    "document id",
    "release version",
    "release date",
    "document type",
    "applies to",
    "vendor",
    "product family",
    "platform",
    "version",
    "published date",
}

SEMANTIC_SECTIONS = {
    "overview": "overview",
    "supported components": "supported_components",
    "compatibility requirements": "compatibility_requirements",
    "certified configurations": "certified_configurations",
    "unsupported configurations": "unsupported_configurations",
    "known issues": "known_issues",
    "fixed issues": "fixed_issues",
    "upgrade requirements": "upgrade_requirements",
    "firmware requirements": "firmware_requirements",
    "driver requirements": "driver_requirements",
    "security updates": "security_updates",
    "remediation guidance": "remediation_guidance",
}


@dataclass
class SemanticChunk:
    page_number: int
    chunk_type: str
    section_title: str | None
    text: str
    source_excerpt: str
    extraction_method: str
    quality_score: float
    bbox_json: dict | None
    metadata_json: dict = field(default_factory=dict)
    rule_likelihood: str = "low"
    send_to_llm: bool = False
    source_parser: str | None = None
    source_chunker: str | None = None
    source_docling_ref: str | None = None
    section_path_json: list | None = None
    semantic_zone: str | None = None
    semantic_zone_confidence: float | None = None
    classification_signals_json: list | None = None
    llm_usage: str = "ignore"
    rule_signal_score: int = 0
    rule_signals_json: list | None = None
    table_headers_json: list | None = None
    table_row_json: dict | None = None
    context_before: str | None = None
    context_after: str | None = None
    deduplication_status: str = "kept"
    token_estimate: int = 0
    character_count: int = 0


@dataclass
class ChunkingStats:
    rejected: int = 0
    deduplicated: int = 0


class ChunkingService:
    def __init__(self) -> None:
        self.stats = ChunkingStats()
        self.settings = get_settings()
        self.scorer = RuleSignalScorer()

    def create_chunks(self, document_id: str, blocks: list[ExtractedBlock]) -> list[DocumentChunk]:
        self.stats = ChunkingStats()
        semantic_chunks: list[SemanticChunk] = []
        for block in blocks:
            semantic_chunks.extend(self._chunks_from_block(block))

        semantic_chunks = self._deduplicate(semantic_chunks)
        return [
            DocumentChunk(
                document_id=document_id,
                page_number=chunk.page_number,
                chunk_index=index,
                chunk_type=chunk.chunk_type,
                section_title=chunk.section_title,
                text=chunk.text,
                source_excerpt=chunk.source_excerpt,
                extraction_method=chunk.extraction_method,
                quality_score=chunk.quality_score,
                rule_likelihood=chunk.rule_likelihood,
                send_to_llm=chunk.send_to_llm,
                source_parser=chunk.source_parser,
                source_chunker=chunk.source_chunker,
                source_docling_ref=chunk.source_docling_ref,
                section_path_json=chunk.section_path_json,
                semantic_zone=chunk.semantic_zone,
                semantic_zone_confidence=chunk.semantic_zone_confidence,
                classification_signals_json=chunk.classification_signals_json,
                llm_usage=chunk.llm_usage,
                rule_signal_score=chunk.rule_signal_score,
                rule_signals_json=chunk.rule_signals_json,
                table_headers_json=chunk.table_headers_json,
                table_row_json=chunk.table_row_json,
                context_before=chunk.context_before,
                context_after=chunk.context_after,
                deduplication_status=chunk.deduplication_status,
                token_estimate=chunk.token_estimate,
                character_count=chunk.character_count,
                bbox_json=chunk.bbox_json,
                metadata_json=chunk.metadata_json,
            )
            for index, chunk in enumerate(semantic_chunks)
        ]

    def _chunks_from_block(self, block: ExtractedBlock) -> list[SemanticChunk]:
        text = self._clean_text(block.text)
        if not text:
            return []

        if block.block_type == "table_row":
            return self._table_row_chunk(block, text)

        sections = self._semantic_sections(text)
        chunks: list[SemanticChunk] = []
        metadata_chunk = self._metadata_chunk(block, text)
        if metadata_chunk:
            chunks.append(metadata_chunk)
            text = self._remove_metadata_text(text)
            sections = self._semantic_sections(text)

        for title, body in sections:
            body = self._clean_text(body)
            if not body:
                continue
            zone = self._semantic_zone(title)
            chunks.extend(self._section_chunks(block, title, body, zone))

        if not chunks and text:
            semantic = self._build_semantic_chunk(
                block=block,
                chunk_type="prose",
                section_title=block.section_title,
                text=text,
                semantic_zone=self._semantic_zone(block.section_title),
                strategy="single_block",
            )
            if semantic:
                chunks.append(semantic)
        return chunks

    def _section_chunks(self, block: ExtractedBlock, title: str | None, body: str, zone: str) -> list[SemanticChunk]:
        chunks: list[SemanticChunk] = []
        for unit in self._table_aware_units(body):
            if unit["kind"] == "table_row":
                semantic = self._build_semantic_chunk(
                    block=block,
                    chunk_type="component_table_row",
                    section_title=title,
                    text=unit["text"],
                    semantic_zone=self._semantic_zone_override(zone, "component_table_row", unit["text"]),
                    strategy="markdown_table_row_with_headers",
                    extra_metadata=unit["metadata"],
                )
                if semantic:
                    chunks.append(semantic)
                continue

            for chunk_type, chunk_text in self._rule_aware_units(unit["text"], zone):
                semantic = self._build_semantic_chunk(
                    block=block,
                    chunk_type=chunk_type,
                    section_title=title,
                    text=chunk_text,
                    semantic_zone=zone,
                    strategy="section_rule_aware",
                )
                if semantic:
                    chunks.append(semantic)
        return chunks

    def _table_aware_units(self, text: str) -> list[dict]:
        lines = text.splitlines()
        units: list[dict] = []
        buffer: list[str] = []
        index = 0
        previous_headers: list[str] | None = None
        while index < len(lines):
            if self._is_markdown_table_start(lines, index):
                if buffer:
                    units.append({"kind": "text", "text": "\n".join(buffer).strip(), "metadata": {}})
                    buffer = []
                table_lines, next_index = self._collect_markdown_table(lines, index)
                table_units, previous_headers = self._markdown_table_row_units(table_lines, previous_headers)
                units.extend(table_units)
                index = next_index
                continue
            buffer.append(lines[index])
            index += 1

        if buffer:
            units.append({"kind": "text", "text": "\n".join(buffer).strip(), "metadata": {}})
        return [unit for unit in units if unit["text"]]

    def _is_markdown_table_start(self, lines: list[str], index: int) -> bool:
        return (
            index + 1 < len(lines)
            and self._is_markdown_table_row(lines[index])
            and self._is_markdown_separator_row(lines[index + 1])
        )

    def _collect_markdown_table(self, lines: list[str], index: int) -> tuple[list[str], int]:
        table_lines: list[str] = []
        while index < len(lines) and self._is_markdown_table_row(lines[index]):
            table_lines.append(lines[index])
            index += 1
        return table_lines, index

    def _markdown_table_row_units(
        self,
        table_lines: list[str],
        previous_headers: list[str] | None = None,
    ) -> tuple[list[dict], list[str] | None]:
        if len(table_lines) < 3:
            return [{"kind": "text", "text": "\n".join(table_lines).strip(), "metadata": {}}], previous_headers

        headers = self._markdown_cells(table_lines[0])
        data_lines = [line for line in table_lines[2:] if not self._is_markdown_separator_row(line)]
        if previous_headers and len(previous_headers) == len(headers) and self._looks_like_table_data(headers):
            data_lines = [table_lines[0], *data_lines]
            headers = previous_headers
        data_rows = [self._markdown_cells(line) for line in data_lines]
        units: list[dict] = []
        for row_number, values in enumerate(data_rows, 1):
            if not values or all(not value for value in values):
                continue
            normalized_values = values[: len(headers)]
            if len(normalized_values) < len(headers):
                normalized_values.extend([""] * (len(headers) - len(normalized_values)))
            row_text = " | ".join(
                f"{header}: {value}" if header else value
                for header, value in zip(headers, normalized_values, strict=False)
                if header or value
            )
            row = dict(zip(headers, normalized_values, strict=False))
            units.append(
                {
                    "kind": "table_row",
                    "text": row_text,
                    "metadata": {
                        "headers": headers,
                        "values": normalized_values,
                        "row_number": row_number,
                        "table_row": row,
                        "table_source": "markdown_table",
                        "table_row_markdown": self._markdown_row(headers, normalized_values),
                    },
                }
            )
        return units, headers

    def _markdown_cells(self, line: str) -> list[str]:
        stripped = line.strip()
        if stripped.startswith("|"):
            stripped = stripped[1:]
        if stripped.endswith("|"):
            stripped = stripped[:-1]
        return [cell.strip() for cell in stripped.split("|")]

    def _markdown_row(self, headers: list[str], values: list[str]) -> str:
        return " | ".join(f"{header}: {value}" for header, value in zip(headers, values, strict=False))

    def _looks_like_table_data(self, cells: list[str]) -> bool:
        if not cells:
            return False
        header_words = {"component", "version", "minimum version", "current release", "condition", "action required", "cve / id", "description", "fixed in"}
        if any(cell.strip().lower() in header_words for cell in cells):
            return False
        return any(re.search(r"\bv?\d+(?:\.\d+)+(?:\.x)?\b", cell, flags=re.IGNORECASE) for cell in cells)

    def _is_markdown_table_row(self, line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.count("|") >= 2

    def _is_markdown_separator_row(self, line: str) -> bool:
        cells = self._markdown_cells(line)
        if not cells:
            return False
        return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells if cell.strip())

    def _table_row_chunk(self, block: ExtractedBlock, text: str) -> list[SemanticChunk]:
        headers = block.metadata_json.get("headers")
        values = block.metadata_json.get("values")
        row_number = block.metadata_json.get("row_number")
        if headers and values and len(headers) == len(values):
            text = " | ".join(f"{header}: {value}" for header, value in zip(headers, values, strict=False))
        table_row = dict(zip(headers or [], values or [], strict=False)) if headers and values else block.metadata_json.get("row")
        semantic = self._build_semantic_chunk(
            block=block,
            chunk_type="component_table_row",
            section_title=block.section_title,
            text=text,
            semantic_zone="compatibility_requirements",
            strategy="table_row_with_headers",
            extra_metadata={"headers": headers, "row_number": row_number, "table_row": table_row},
        )
        return [semantic] if semantic else []

    def _metadata_chunk(self, block: ExtractedBlock, text: str) -> SemanticChunk | None:
        lines = [line.strip("# ").strip() for line in text.splitlines() if line.strip()]
        metadata_lines: list[str] = []
        title_parts: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            lowered = line.lower().rstrip(":")
            if lowered in METADATA_LABELS:
                value = lines[index + 1] if index + 1 < len(lines) and not self._is_label(lines[index + 1]) else ""
                metadata_lines.append(f"{line.rstrip(':')}: {value}".strip())
                index += 2 if value else 1
                continue
            if ":" in line and line.split(":", 1)[0].strip().lower() in METADATA_LABELS:
                metadata_lines.append(line)
            elif len(metadata_lines) == 0 and len(title_parts) < 2 and not self._is_section_heading(line):
                title_parts.append(line)
            index += 1

        if not metadata_lines:
            return None

        section_title = " ".join(title_parts).strip() or block.section_title or "Document Metadata"
        return self._build_semantic_chunk(
            block=block,
            chunk_type="document_metadata",
            section_title=section_title,
            text="\n".join(metadata_lines),
            semantic_zone="document_metadata",
            strategy="metadata_grouping",
        )

    def _remove_metadata_text(self, text: str) -> str:
        lines = [line for line in text.splitlines()]
        cleaned: list[str] = []
        skip_next = False
        for line in lines:
            stripped = line.strip("# ").strip()
            if skip_next:
                skip_next = False
                continue
            if stripped.lower().rstrip(":") in METADATA_LABELS:
                skip_next = True
                continue
            if ":" in stripped and stripped.split(":", 1)[0].strip().lower() in METADATA_LABELS:
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    def _semantic_sections(self, text: str) -> list[tuple[str | None, str]]:
        lines = text.splitlines()
        sections: list[tuple[str | None, list[str]]] = []
        current_title: str | None = None
        current_body: list[str] = []

        for line in lines:
            stripped = line.strip()
            if self._is_section_heading(stripped):
                if current_title or current_body:
                    sections.append((current_title, current_body))
                current_title = stripped.lstrip("#").strip()
                current_body = []
            else:
                current_body.append(line)
        if current_title or current_body:
            sections.append((current_title, current_body))

        return [(title, "\n".join(body).strip()) for title, body in sections if "\n".join(body).strip()]

    def _rule_aware_units(self, text: str, semantic_zone: str) -> list[tuple[str, str]]:
        if semantic_zone == "overview" and not self._keywords_detected(text):
            return [("overview", text)]
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", text) if paragraph.strip()]
        if len(paragraphs) > 1:
            return [
                (self._chunk_type_for_text(paragraph, semantic_zone), paragraph)
                for paragraph in paragraphs
            ]

        sentences = self._sentences(text)
        if len(sentences) <= 1:
            return [(self._chunk_type_for_text(text, semantic_zone), text)]

        units: list[tuple[str, str]] = []
        buffer: list[str] = []
        for sentence in sentences:
            chunk_type = self._chunk_type_for_text(sentence, semantic_zone)
            if chunk_type in {"requirement_rule", "compound_requirement", "unsupported_configuration", "known_issue_fixed"}:
                if buffer:
                    units.append((self._chunk_type_for_text(" ".join(buffer), semantic_zone), " ".join(buffer)))
                    buffer = []
                units.append((chunk_type, sentence))
            else:
                buffer.append(sentence)
        if buffer:
            units.append((self._chunk_type_for_text(" ".join(buffer), semantic_zone), " ".join(buffer)))
        return units

    def _build_semantic_chunk(
        self,
        block: ExtractedBlock,
        chunk_type: str,
        section_title: str | None,
        text: str,
        semantic_zone: str,
        strategy: str,
        extra_metadata: dict | None = None,
    ) -> SemanticChunk | None:
        clean_text = self._clean_text(text)
        if self._is_suspicious(clean_text, chunk_type):
            self.stats.rejected += 1
            if not self.settings.debug_store_rejected_chunks:
                return None
            chunk_type = "rejected"

        keywords = self._keywords_detected(clean_text)
        semantic_zone = self._semantic_zone_override(semantic_zone, chunk_type, clean_text)
        score, rule_signals, rule_likelihood = self.scorer.score(clean_text, semantic_zone=semantic_zone, chunk_type=chunk_type)
        llm_usage = self._llm_usage(chunk_type, semantic_zone, rule_likelihood)
        send_to_llm = llm_usage == "rule_extraction"
        source_parser = block.metadata_json.get("source_parser") or block.extraction_method
        source_chunker = block.metadata_json.get("source_chunker") or (
            "docling_hybrid_chunker" if block.extraction_method == "docling" else "compatiq_semantic_chunker"
        )
        table_headers = (extra_metadata or {}).get("headers")
        table_row = (extra_metadata or {}).get("table_row")

        metadata = {
            **block.metadata_json,
            **(extra_metadata or {}),
            "source_block_type": block.block_type,
            "strategy": strategy,
            "keywords_detected": keywords,
            "semantic_zone": semantic_zone,
            "llm_usage": llm_usage,
            "rule_score": score,
            "rule_signals": rule_signals,
            "original_blocks": [block.text[:500]],
            "extractor_selected_by_profile": block.metadata_json.get("extractor_selected_by_profile"),
            "deduplication_status": "kept",
        }
        return SemanticChunk(
            page_number=block.page_number,
            chunk_type=chunk_type,
            section_title=section_title,
            text=clean_text,
            source_excerpt=self._source_excerpt(clean_text),
            extraction_method=block.extraction_method,
            quality_score=block.quality_score,
            bbox_json=block.bbox_json,
            metadata_json=metadata,
            rule_likelihood=rule_likelihood,
            send_to_llm=send_to_llm,
            source_parser=source_parser,
            source_chunker=source_chunker,
            source_docling_ref=block.metadata_json.get("source_docling_ref"),
            section_path_json=[section_title] if section_title else [],
            semantic_zone=semantic_zone,
            semantic_zone_confidence=self._semantic_zone_confidence(semantic_zone, score),
            classification_signals_json=self._classification_signals(semantic_zone, clean_text),
            llm_usage=llm_usage,
            rule_signal_score=score,
            rule_signals_json=rule_signals,
            table_headers_json=table_headers,
            table_row_json=table_row,
            deduplication_status="kept",
            token_estimate=max(1, len(clean_text.split()) * 4 // 3),
            character_count=len(clean_text),
        )

    def _deduplicate(self, chunks: list[SemanticChunk]) -> list[SemanticChunk]:
        selected: dict[str, SemanticChunk] = {}
        for chunk in chunks:
            key = self._dedupe_key(chunk.text)
            if not key:
                continue
            existing = selected.get(key)
            if existing is None:
                selected[key] = chunk
                continue
            self.stats.deduplicated += 1
            winner = self._prefer_chunk(existing, chunk)
            loser = chunk if winner is existing else existing
            winner.metadata_json["deduplication_status"] = "kept_after_duplicate"
            winner.metadata_json["deduplicated_from"] = loser.extraction_method
            winner.deduplication_status = "kept_after_duplicate"
            selected[key] = winner
        return list(selected.values())

    def _prefer_chunk(self, first: SemanticChunk, second: SemanticChunk) -> SemanticChunk:
        if first.metadata_json.get("extractor_selected_by_profile") == first.extraction_method:
            return first
        if second.metadata_json.get("extractor_selected_by_profile") == second.extraction_method:
            return second
        priority = {"docling": 5, "pymupdf": 4, "chandra_ocr": 3, "text": 2, "csv": 1}
        if priority.get(second.extraction_method, 0) > priority.get(first.extraction_method, 0):
            return second
        if second.quality_score > first.quality_score:
            return second
        return first

    def _clean_text(self, text: str) -> str:
        text = html.unescape(text or "")
        text = text.replace("\u2022", "-").replace("\u2013", "-").replace("\u2014", "-")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = self._join_label_value_pairs(text)
        return text.strip()

    def _join_label_value_pairs(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        output: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            lowered = line.lower().rstrip(":")
            if lowered in METADATA_LABELS and index + 1 < len(lines):
                next_line = lines[index + 1]
                if next_line and not self._is_label(next_line):
                    output.append(f"{line.rstrip(':')}: {next_line}")
                    index += 2
                    continue
            output.append(line)
            index += 1
        return "\n".join(output)

    def _is_section_heading(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        if stripped.startswith("#"):
            return True
        if re.match(r"^\d+(?:\.\d+)*\.\s+\S+", stripped):
            return True
        if re.match(r"^version\s+v?\d+(?:\.\d+)*", stripped, re.IGNORECASE):
            return True
        lowered = stripped.lower().rstrip(":")
        return lowered in SEMANTIC_SECTIONS

    def _semantic_zone(self, title: str | None) -> str:
        if not title:
            return "body"
        lowered = re.sub(r"^\d+(?:\.\d+)*\.\s*", "", title.lower().strip("# :"))
        return SEMANTIC_SECTIONS.get(lowered, "body")

    def _sentences(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", re.sub(r"\s+", " ", text).strip())
        return [part.strip() for part in parts if part.strip()]

    def _chunk_type_for_text(self, text: str, semantic_zone: str) -> str:
        lowered = text.lower()
        has_rule_signal = any(
            word in lowered
            for word in ("requires", "required", "minimum", "or later", "at least", "must", "not supported", "unsupported", "incompatible")
        )
        if semantic_zone == "overview" and not has_rule_signal:
            return "overview"
        if "not supported" in lowered or "unsupported" in lowered or "incompatible" in lowered:
            return "unsupported_configuration"
        if "with " in lowered and any(word in lowered for word in ("requires", "required", "must")):
            return "compound_requirement"
        if any(word in lowered for word in ("requires", "required", "minimum", "or later", "at least", "must")):
            return "minimum_version_requirement" if any(word in lowered for word in ("minimum", "or later", "at least")) else "compatibility_requirement"
        if any(word in lowered for word in ("fixed an issue", "corrected an issue", "added support", "back-flashing")):
            return "fixed_issue"
        if semantic_zone == "overview":
            return "overview"
        return semantic_zone if semantic_zone != "body" else "prose"

    def _semantic_zone_override(self, semantic_zone: str, chunk_type: str, text: str) -> str:
        lowered = text.lower()
        if chunk_type == "unsupported_configuration":
            return "unsupported_configurations"
        if chunk_type in {"minimum_version_requirement", "compatibility_requirement", "compound_requirement"}:
            return "compatibility_requirements"
        if chunk_type == "fixed_issue":
            return "fixed_issues"
        if semantic_zone not in {"body", "unknown"}:
            return semantic_zone
        if "before upgrading" in lowered or "after upgrading" in lowered:
            return "upgrade_requirements"
        return semantic_zone

    def _llm_usage(self, chunk_type: str, semantic_zone: str, rule_likelihood: str) -> str:
        if chunk_type == "document_metadata" or semantic_zone == "document_metadata":
            return "global_context"
        if chunk_type == "overview" or semantic_zone == "overview":
            return "background_context"
        if chunk_type == "rejected":
            return "ignore"
        if chunk_type in {
            "minimum_version_requirement",
            "compatibility_requirement",
            "compound_requirement",
            "unsupported_configuration",
            "component_table_row",
            "fixed_issue",
            "known_issue_fixed",
        }:
            return "rule_extraction" if rule_likelihood in {"high", "medium"} else "evidence_only"
        if rule_likelihood == "high" or (rule_likelihood == "medium" and self.settings.send_medium_likelihood_chunks):
            return "rule_extraction"
        return "evidence_only" if rule_likelihood == "low" and semantic_zone != "unknown" else "ignore"

    def _semantic_zone_confidence(self, semantic_zone: str, score: int) -> float:
        if semantic_zone == "unknown":
            return 0.25
        if semantic_zone in {"document_metadata", "overview"}:
            return 0.9
        return min(0.95, 0.55 + max(score, 0) * 0.06)

    def _classification_signals(self, semantic_zone: str, text: str) -> list[str]:
        signals = []
        lowered = text.lower()
        if semantic_zone != "unknown":
            signals.append(f"classified as {semantic_zone}")
        for token in ("requires", "not supported", "bios", "firmware", "driver", "back-flashing", "processor"):
            if token in lowered:
                signals.append(f"body contains {token}")
        return signals

    def _rule_likelihood(self, text: str, chunk_type: str, semantic_zone: str) -> tuple[str, int]:
        lowered = text.lower()
        score = 0
        if any(word in lowered for word in ("requires", "required", "must")):
            score += 3
        if any(word in lowered for word in ("not supported", "unsupported", "incompatible")):
            score += 3
        if any(word in lowered for word in ("minimum", "or later", "at least")):
            score += 2
        if any(word in lowered for word in ("fixed", "corrected an issue", "added support", "back-flashing")):
            score += 2
        if any(word in lowered for word in ("bios", "firmware", "driver", "os", "agent")):
            score += 1
        if re.search(r"\bv?\d+(?:\.\d+)+(?:\.x)?\b", lowered):
            score += 1
        if chunk_type == "document_metadata" or semantic_zone == "metadata":
            score -= 3
        if chunk_type == "overview" or semantic_zone == "overview":
            score -= 2
        if self._is_label(text) or self._is_version_or_date(text):
            score -= 2
        if score >= 5:
            return "high", score
        if score >= 2:
            return "medium", score
        return "low", score

    def _keywords_detected(self, text: str) -> list[str]:
        lowered = text.lower()
        return [keyword for keyword in RULE_KEYWORDS if keyword in lowered]

    def _is_suspicious(self, text: str, chunk_type: str) -> bool:
        if not text:
            return True
        if chunk_type == "document_metadata":
            return False
        if self._is_version_or_date(text):
            return True
        if self._is_label(text):
            return True
        if self._is_section_heading(text) and len(text.splitlines()) == 1:
            return True
        return len(text.split()) <= 2 and not self._keywords_detected(text) and not re.search(r"[.!?]", text)

    def _is_version_or_date(self, text: str) -> bool:
        stripped = text.strip()
        return bool(
            re.fullmatch(r"v?\d+(?:\.\d+)+(?:\.x)?", stripped, re.IGNORECASE)
            or re.fullmatch(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", stripped)
            or re.fullmatch(r"\d{4}-\d{2}-\d{2}", stripped)
            or re.fullmatch(r"\d+", stripped)
        )

    def _is_label(self, text: str) -> bool:
        stripped = text.strip().strip(":")
        lowered = stripped.lower()
        if lowered in METADATA_LABELS:
            return True
        if re.search(r"[.!?]", stripped):
            return False
        return len(stripped.split()) <= 4 and not re.search(r"\d", stripped)

    def _source_excerpt(self, text: str) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        return compact[:500]

    def _dedupe_key(self, text: str) -> str:
        normalized = html.unescape(text).lower()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized
