from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    extraction_jobs: Mapped[list["ExtractionJob"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    profiles: Mapped[list["DocumentProfile"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    rule_candidates: Mapped[list["RuleCandidate"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    @property
    def display_name(self) -> str:
        return self.original_filename or self.filename or self.document_id

    @property
    def file_type(self) -> str:
        if self.content_type:
            return self.content_type
        suffix = self.filename.rsplit(".", 1)[-1] if "." in self.filename else ""
        return suffix.lower() or self.source_type


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.document_id"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    document: Mapped[Document] = relationship(back_populates="extraction_jobs")


class DocumentProfile(Base):
    __tablename__ = "document_profiles"

    profile_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.document_id"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    page_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_extractor: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    signals_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    document: Mapped[Document] = relationship(back_populates="profiles")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.document_id"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    rule_likelihood: Mapped[str] = mapped_column(String(20), nullable=False, default="low", index=True)
    send_to_llm: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    source_parser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_chunker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_docling_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    section_path_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    semantic_zone: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    semantic_zone_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_signals_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    llm_usage: Mapped[str] = mapped_column(String(50), nullable=False, default="ignore", index=True)
    rule_signal_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_signals_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    table_headers_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    table_row_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    context_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    deduplication_status: Mapped[str] = mapped_column(String(50), nullable=False, default="kept")
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bbox_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")
    rule_candidates: Mapped[list["RuleCandidate"]] = relationship(back_populates="source_chunk")


class RuleCandidate(Base):
    __tablename__ = "rule_candidates"

    candidate_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.document_id"),
        nullable=False,
        index=True,
    )
    source_chunk_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_chunks.chunk_id"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    condition_logic: Mapped[str | None] = mapped_column(String(50), nullable=True)
    conditions_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    requirement_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending_review", index=True)
    normalization_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending_normalization",
        index=True,
    )
    raw_llm_output_json: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    normalized_rule_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    validation_errors_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    document: Mapped[Document] = relationship(back_populates="rule_candidates")
    source_chunk: Mapped[DocumentChunk] = relationship(back_populates="rule_candidates")
