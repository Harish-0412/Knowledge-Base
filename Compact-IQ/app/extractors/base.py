from dataclasses import dataclass, field
from typing import Protocol

from app.db.models import Document, DocumentProfile


@dataclass
class ExtractedBlock:
    page_number: int
    block_type: str
    text: str
    extraction_method: str
    section_title: str | None = None
    quality_score: float = 1.0
    bbox_json: dict | None = None
    metadata_json: dict = field(default_factory=dict)


class Extractor(Protocol):
    def extract(self, document: Document, profiles: list[DocumentProfile]) -> list[ExtractedBlock]:
        ...
