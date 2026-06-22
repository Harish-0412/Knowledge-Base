from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT.parent / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CompatIQ Document Intelligence Service"
    app_env: str = "development"
    app_debug: bool = True

    database_url: str | None = "sqlite:///./compatiq.db"

    upload_dir: str = "storage/uploads"
    extracted_dir: str = "storage/extracted"
    export_dir: str = "storage/exports"

    llm_provider: str = "ollama"
    use_mock_llm: bool = False
    allow_mock_llm_rule_extraction: bool = True
    use_mock_ocr: bool = False
    enable_docling: bool = True
    docling_enabled: bool = True
    preferred_parser: str = "docling"
    docling_table_structure: bool = True
    docling_table_mode: str = "accurate"
    docling_ocr_enabled: bool = False
    enable_chandra_ocr: bool = False
    chandra_ocr_enabled: bool = False
    pymupdf_fallback_enabled: bool = True
    chandra_api_url: str = ""
    chandra_timeout_seconds: int = 120
    llm_json_repair_retry: bool = False
    debug_extractor_comparison: bool = False
    send_medium_likelihood_chunks: bool = True
    debug_store_rejected_chunks: bool = False
    chunker_mode: str = "docling_hybrid_plus_compatiq"
    hybrid_chunker_max_tokens: int = 800
    hybrid_chunker_merge_peers: bool = True
    hybrid_chunker_repeat_table_headers: bool = True
    docling_save_document_json: bool = True
    docling_save_markdown: bool = True
    docling_save_hybrid_chunks: bool = True
    enable_llm_zone_classification: bool = False
    extraction_pipeline_mode: str = "processing_lanes"
    enable_deterministic_table_extraction: bool = True
    enable_llm_prose_extraction: bool = True
    enable_llm_table_extraction: bool = False
    quality_gate_strict: bool = False
    export_pipeline_debug_files: bool = True

    ollama_base_url: str = "http://localhost:11434"
    ollama_generate_path: str = "/api/generate"
    ollama_api_key: str = ""
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = 90
    assistant_ollama_model: str = "llama3.1:8b"
    assistant_max_answer_chars: int = 1200

    nvd_api_key: str = ""
    nvd_timeout_seconds: int = 45

    max_upload_mb: int = 25

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
