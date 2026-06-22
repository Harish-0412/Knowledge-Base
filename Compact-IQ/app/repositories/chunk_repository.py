from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk, RuleCandidate


class ChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def replace_chunks(self, document_id: str, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        old_chunk_ids = select(DocumentChunk.chunk_id).where(DocumentChunk.document_id == document_id)
        self.db.execute(
            delete(RuleCandidate).where(
                or_(
                    RuleCandidate.document_id == document_id,
                    RuleCandidate.source_chunk_id.in_(old_chunk_ids),
                )
            )
        )
        self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def list_chunks_for_document(
        self,
        document_id: str,
        *,
        send_to_llm: bool | None = None,
        rule_likelihood: str | None = None,
        chunk_type: str | None = None,
        llm_usage: str | None = None,
        semantic_zone: str | None = None,
    ) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc(), DocumentChunk.chunk_id.asc())
        )
        if send_to_llm is not None:
            statement = statement.where(DocumentChunk.send_to_llm.is_(send_to_llm))
        if rule_likelihood:
            statement = statement.where(DocumentChunk.rule_likelihood == rule_likelihood)
        if chunk_type:
            statement = statement.where(DocumentChunk.chunk_type == chunk_type)
        if llm_usage:
            statement = statement.where(DocumentChunk.llm_usage == llm_usage)
        if semantic_zone:
            statement = statement.where(DocumentChunk.semantic_zone == semantic_zone)
        return list(self.db.scalars(statement).all())

    def get_chunk(self, chunk_id: int) -> DocumentChunk | None:
        return self.db.get(DocumentChunk, chunk_id)

    def get_by_ids(self, chunk_ids: set[int]) -> list[DocumentChunk]:
        if not chunk_ids:
            return []
        statement = select(DocumentChunk).where(DocumentChunk.chunk_id.in_(chunk_ids))
        return list(self.db.scalars(statement).all())
