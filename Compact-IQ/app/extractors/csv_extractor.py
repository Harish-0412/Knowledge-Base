import csv
from pathlib import Path

from app.db.models import Document, DocumentProfile
from app.extractors.base import ExtractedBlock


class CSVExtractor:
    def extract(self, document: Document, profiles: list[DocumentProfile]) -> list[ExtractedBlock]:
        blocks: list[ExtractedBlock] = []
        with Path(document.file_path).open("r", encoding="utf-8", errors="replace", newline="") as file:
            reader = csv.DictReader(file)
            headers = reader.fieldnames or []
            for row_index, row in enumerate(reader, start=1):
                row_text = "\n".join(f"{header}: {row.get(header, '')}" for header in headers)
                blocks.append(
                    ExtractedBlock(
                        page_number=1,
                        block_type="table_row",
                        text=row_text,
                        extraction_method="csv",
                        quality_score=0.95,
                        metadata_json={
                            "headers": headers,
                            "values": [row.get(header, "") for header in headers],
                            "row_index": row_index,
                            "row_number": row_index,
                            "row": dict(row),
                        },
                    )
                )

        if not blocks:
            raw_text = Path(document.file_path).read_text(encoding="utf-8", errors="replace")
            blocks.append(
                ExtractedBlock(
                    page_number=1,
                    block_type="table",
                    text=raw_text,
                    extraction_method="csv",
                    quality_score=0.6,
                    metadata_json={"headers": headers},
                )
            )
        return blocks
