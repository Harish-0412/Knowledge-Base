from app.db import models  # noqa: F401
from app.db.session import Base, engine
from sqlalchemy import inspect, text


def main() -> None:
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured. Set it before creating tables.")

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        _ensure_document_chunk_columns(connection)
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_rule_candidates_review_status ON rule_candidates (review_status)")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_rule_candidates_normalization_status "
                "ON rule_candidates (normalization_status)"
            )
        )
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_document_chunks_rule_likelihood ON document_chunks (rule_likelihood)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_document_chunks_send_to_llm ON document_chunks (send_to_llm)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_document_chunks_semantic_zone ON document_chunks (semantic_zone)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_document_chunks_llm_usage ON document_chunks (llm_usage)"))
    print(
        "Created database tables: documents, extraction_jobs, document_profiles, "
        "document_chunks, rule_candidates"
    )


def _ensure_document_chunk_columns(connection) -> None:
    inspector = inspect(connection)
    existing = {column["name"] for column in inspector.get_columns("document_chunks")}
    columns = {
        "rule_likelihood": "VARCHAR(20) NOT NULL DEFAULT 'low'",
        "send_to_llm": "BOOLEAN NOT NULL DEFAULT FALSE",
        "source_parser": "VARCHAR(100)",
        "source_chunker": "VARCHAR(100)",
        "source_docling_ref": "VARCHAR(255)",
        "section_path_json": "JSON",
        "semantic_zone": "VARCHAR(100)",
        "semantic_zone_confidence": "FLOAT",
        "classification_signals_json": "JSON",
        "llm_usage": "VARCHAR(50) NOT NULL DEFAULT 'ignore'",
        "rule_signal_score": "INTEGER NOT NULL DEFAULT 0",
        "rule_signals_json": "JSON",
        "table_headers_json": "JSON",
        "table_row_json": "JSON",
        "context_before": "TEXT",
        "context_after": "TEXT",
        "deduplication_status": "VARCHAR(50) NOT NULL DEFAULT 'kept'",
        "token_estimate": "INTEGER NOT NULL DEFAULT 0",
        "character_count": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, definition in columns.items():
        if name not in existing:
            connection.execute(text(f"ALTER TABLE document_chunks ADD COLUMN {name} {definition}"))


if __name__ == "__main__":
    main()
