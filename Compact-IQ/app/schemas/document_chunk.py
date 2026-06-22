from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentChunkResponse(BaseModel):
    chunk_id: int
    document_id: str
    page_number: int
    chunk_index: int
    chunk_type: str
    section_title: str | None
    text: str
    source_excerpt: str
    extraction_method: str
    quality_score: float
    rule_likelihood: str
    send_to_llm: bool
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
    token_estimate: int
    character_count: int
    bbox_json: dict | None
    metadata_json: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkListResponse(BaseModel):
    document_id: str
    chunks: list[DocumentChunkResponse]


class DocumentExtractResponse(BaseModel):
    document_id: str
    status: str
    chunks_created: int
    chunks_rejected: int = 0
    chunks_deduplicated: int = 0
    methods_used: list[str]
    preferred_parser: str | None = None
    parser_used: str | None = None
    source_chunker: str | None = None
    semantic_zone_summary: dict[str, int] = {}
    llm_usage_summary: dict[str, int] = {}
    rule_likelihood_summary: dict[str, int] = {}
    llm_input_chunk_count: int = 0
    llm_rule_extraction_chunk_count: int = 0
    warnings: list[str]
