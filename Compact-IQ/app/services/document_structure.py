from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentBlock:
    block_id: str
    document_id: str
    page_number: int
    block_index: int
    block_type: str
    text: str
    level: int | None = None
    bbox: dict | None = None
    source_parser: str = "unknown"
    source_extractor: str = "unknown"
    source_ref: str | None = None
    section_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSection:
    section_id: str
    section_title: str | None
    section_path: list[str]
    level: int
    page_start: int
    page_end: int
    blocks: list[DocumentBlock]
    parent_section_id: str | None = None
    semantic_zone: str = "unknown"
    semantic_zone_confidence: float = 0.0
    classification_signals: list[str] = field(default_factory=list)


class DocumentStructureBuilder:
    def build_sections(self, blocks: list[DocumentBlock]) -> list[DocumentSection]:
        sections: list[DocumentSection] = []
        current_title: str | None = None
        current_path: list[str] = []
        current_blocks: list[DocumentBlock] = []
        current_level = 1

        for block in blocks:
            if block.block_type == "heading" and self._is_meaningful_heading(block.text):
                if current_blocks:
                    sections.append(self._section(len(sections), current_title, current_path, current_level, current_blocks))
                current_title = block.text.strip("# ").strip()
                current_level = block.level or self._heading_level(block.text)
                current_path = [current_title]
                current_blocks = []
                continue
            current_blocks.append(block)

        if current_blocks:
            sections.append(self._section(len(sections), current_title, current_path, current_level, current_blocks))

        if not sections and blocks:
            sections.append(self._section(0, None, [], 1, blocks))
        return sections

    def _section(
        self,
        index: int,
        title: str | None,
        path: list[str],
        level: int,
        blocks: list[DocumentBlock],
    ) -> DocumentSection:
        return DocumentSection(
            section_id=f"SEC-{index + 1:03d}",
            section_title=title,
            section_path=path,
            level=level,
            page_start=min(block.page_number for block in blocks),
            page_end=max(block.page_number for block in blocks),
            blocks=blocks,
        )

    def _heading_level(self, text: str) -> int:
        stripped = text.lstrip()
        return len(stripped) - len(stripped.lstrip("#")) or 1

    def _is_meaningful_heading(self, text: str) -> bool:
        stripped = text.strip("# ").strip()
        return bool(stripped and len(stripped) > 2 and not stripped.isdigit())
