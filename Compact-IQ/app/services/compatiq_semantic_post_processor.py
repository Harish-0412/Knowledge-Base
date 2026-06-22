from __future__ import annotations

from app.db.models import DocumentChunk
from app.extractors.base import ExtractedBlock
from app.services.chunking_service import ChunkingService


class CompatIQSemanticPostProcessor:
    def process(self, document_id: str, blocks: list[ExtractedBlock]) -> tuple[list[DocumentChunk], ChunkingService]:
        service = ChunkingService()
        return service.create_chunks(document_id, blocks), service
