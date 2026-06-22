# Member 3 Handoff

## Module Responsibility

Member 3 owns document intelligence from uploaded compatibility documents through normalized rule candidates ready for human review.

The service does:

- Store uploaded documents.
- Profile documents and select extraction strategy.
- Prefer Docling for structured documents when enabled, with PyMuPDF/Chandra/TXT/CSV fallback paths.
- Convert parser output into structure-aware CompatIQ semantic chunks.
- Score semantic chunks with `semantic_zone`, `llm_usage`, `rule_signal_score`, `rule_likelihood`, and `send_to_llm`.
- Extract raw rule candidates with mock LLM or Ollama Cloud.
- Normalize candidates into the SOT-compatible candidate shape.
- Export normalized candidates for teammate services.
- Write local JSON snapshots for demo/debug handoff.

The service does not:

- Approve rules.
- Create final approved rules.
- Run compliance scans.
- Build the Neo4j graph.
- Generate violations.

## Endpoints

Health:

- `GET /api/health`
- `GET /api/health/db`
- `GET /api/health/llm`

Documents:

- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `POST /api/documents/{document_id}/profile`
- `GET /api/documents/{document_id}/profile`
- `POST /api/documents/{document_id}/extract`
- `GET /api/documents/{document_id}/chunks`
- `POST /api/documents/{document_id}/extract-rules`
- `GET /api/documents/{document_id}/rule-candidates`
- `POST /api/documents/{document_id}/normalize-rule-candidates`
- `POST /api/documents/{document_id}/run-docintel-pipeline`
- `GET /api/documents/{document_id}/exports`

Chunks:

- `GET /api/chunks/{chunk_id}`

Rule candidates:

- `GET /api/rule-candidates`
- `GET /api/rule-candidates/{candidate_id}`
- `POST /api/rule-candidates/{candidate_id}/normalize`

Export:

- `GET /api/export/document/{document_id}/rule-candidates`

Debug:

- `POST /api/debug/llm-test`
- `POST /api/debug/run-demo-document`

## DB Tables

- `documents`
- `document_profiles`
- `document_chunks`
- `extraction_jobs`
- `rule_candidates`

Important indexes:

- `documents.document_id`
- `document_chunks.document_id`
- `rule_candidates.document_id`
- `rule_candidates.source_chunk_id`
- `rule_candidates.review_status`
- `rule_candidates.normalization_status`

## Output Contract

Final Member 3 output is normalized rule candidates, not approved rules.

Use:

```http
GET /api/export/document/{document_id}/rule-candidates
```

The export returns:

```json
{
  "document_id": "DOC-...",
  "export_type": "normalized_rule_candidates",
  "rule_candidates": []
}
```

Each exported candidate comes from `normalized_rule_json` and preserves:

- `candidate_id`
- `source_document_id`
- `source_chunk_id`
- `source_excerpt`
- `rule_type`
- `condition_logic`
- `conditions`
- `requirements`
- `severity`
- `confidence_score`
- `review_status`

All candidates remain `pending_review` until a future human review module approves or rejects them.

The full pipeline endpoint returns an integration summary:

```json
{
  "document_id": "DOC-...",
  "status": "rules_extracted",
  "profile_count": 1,
  "extractors_used": ["text"],
  "chunks_created": 8,
  "raw_rule_candidates_created": 3,
  "rule_candidates_created": 3,
  "normalized_rule_candidates_created": 3,
  "normalized_candidates": 3,
  "needs_human_review": 1,
  "failed_candidates": 0,
  "exports": {
    "profile": "storage/exports/DOC-.../profile.json",
    "docling_document": "storage/exports/DOC-.../docling_document.json",
    "docling_markdown": "storage/exports/DOC-.../docling_markdown.md",
    "docling_hybrid_chunks": "storage/exports/DOC-.../docling_hybrid_chunks.json",
    "document_blocks": "storage/exports/DOC-.../document_blocks.json",
    "document_sections": "storage/exports/DOC-.../document_sections.json",
    "chunks": "storage/exports/DOC-.../chunks.json",
    "chunks_csv": "storage/exports/DOC-.../chunks.csv",
    "llm_context_pack": "storage/exports/DOC-.../llm_context_pack.json",
    "llm_input_chunks": "storage/exports/DOC-.../llm_input_chunks.json",
    "raw_rule_candidates": "storage/exports/DOC-.../raw_rule_candidates.json",
    "normalized_rule_candidates": "storage/exports/DOC-.../normalized_rule_candidates.json",
    "pipeline_summary": "storage/exports/DOC-.../pipeline_summary.json"
  },
  "warnings": []
}
```

Local JSON snapshots are written under:

```text
storage/exports/{document_id}/
```

Snapshot files:

- `profile.json`
- `docling_document.json`
- `docling_markdown.md`
- `docling_hybrid_chunks.json`
- `document_blocks.json`
- `document_sections.json`
- `chunks.json`
- `chunks.csv`
- `llm_context_pack.json`
- `llm_input_chunks.json`
- `raw_rule_candidates.json`
- `normalized_rule_candidates.json`
- `pipeline_summary.json`

Check local export status with:

```http
GET /api/documents/{document_id}/exports
```

These local files are for demo/debug convenience. PostgreSQL remains the source of truth.

Chunk records include `source_parser`, `source_chunker`, `section_path_json`, `semantic_zone`, `semantic_zone_confidence`, `classification_signals_json`, `llm_usage`, `rule_signal_score`, `rule_signals_json`, `rule_likelihood`, `send_to_llm`, `character_count`, `token_estimate`, table metadata, and `deduplication_status`. Rule extraction uses `llm_usage=rule_extraction` chunks as primary targets. Metadata and overview chunks are included in the LLM context pack but are not primary extraction chunks.

## Known Limitations

- Docling is optional and only runs when installed and `ENABLE_DOCLING=true`.
- Chandra OCR is optional and only runs when `ENABLE_CHANDRA_OCR=true` and `CHANDRA_API_URL` is configured.
- PDF extraction requires PyMuPDF for selectable text.
- Mock LLM is deterministic and useful for tests, not real extraction quality.
- Ollama Cloud endpoint path may need adjustment per deployment.
- Normalization is deterministic and conservative; ambiguous values are marked `needs_human_review`.
- There are no migrations yet; `scripts/create_tables.py` uses SQLAlchemy `create_all`.
- Local JSON exports are snapshots and can be regenerated by rerunning pipeline steps.

## Future Improvements

- Add Alembic migrations.
- Complete Docling structured extraction.
- Harden Docling extraction against more document shapes.
- Add authentication/retry policy for Chandra OCR deployments.
- Add human review workflow.
- Promote approved candidates into approved-rule storage.
- Add JSON Schema validation against SOT files in addition to Pydantic validation.
- Add pagination/filtering for candidate list endpoints.
