from pathlib import Path

from app.db.models import Document, DocumentProfile
from app.extractors.base import ExtractedBlock


class TextExtractor:
    def extract(self, document: Document, profiles: list[DocumentProfile]) -> list[ExtractedBlock]:
        text = Path(document.file_path).read_text(encoding="utf-8", errors="replace")
        return [
            ExtractedBlock(
                page_number=1,
                block_type="text",
                text=text,
                extraction_method="text",
                quality_score=0.95,
                metadata_json={"original_filename": document.original_filename},
            )
        ]
