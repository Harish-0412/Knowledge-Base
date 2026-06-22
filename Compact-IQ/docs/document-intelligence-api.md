# Document Intelligence API

Frontend integration guide for the CompatIQ Document Intelligence layer.

Base URL when running locally:

```text
http://localhost:8001/api
```

All responses use JSON except document upload, which uses `multipart/form-data`.

## Current Frontend Flow

1. Upload a document.
2. Optionally profile it.
3. Extract chunks.
4. Extract and normalize rule candidates.
5. Show rule candidates for human review.
6. Export normalized candidates.

Approval status is present on rule candidates as `review_status`, but there is currently no implemented endpoint to approve, reject, or edit a rule candidate. The frontend can display review state, but backend approval actions need a new update endpoint before they can be persisted.

## Status Values

Document `status` values currently used by the backend:

```text
uploaded
profiled
extracted
rules_extracted
```

Rule candidate `review_status` values supported by the normalized schema:

```text
pending_review
approved
edited
rejected
needs_clarification
```

Current extraction creates candidates mostly as `pending_review`; grounding failures may become `needs_clarification`.

## Error Shape

Expected error response:

```json
{
  "error": {
    "code": "document_not_found",
    "message": "Document was not found.",
    "details": {
      "document_id": "DOC-..."
    }
  }
}
```

Common HTTP statuses:

```text
400 bad request
404 not found
413 upload too large
502 upstream parser/LLM failure
```

## Health

### GET `/health`

Checks that the API process is alive.

Response:

```json
{
  "status": "ok",
  "service": "CompatIQ Document Intelligence",
  "version": "0.1.0"
}
```

### GET `/health/db`

Checks database connectivity.

### GET `/health/llm`

Checks LLM configuration.

Query params:

```text
deep=false
```

Use `deep=true` only from admin/test tooling because it performs a real LLM call.

## Documents

### POST `/documents/upload`

Uploads a source document and creates a document row.

Request:

```http
Content-Type: multipart/form-data
```

Form fields:

```text
file: PDF/DOCX/etc.
```

Example:

```bash
curl -X POST "http://localhost:8001/api/documents/upload" \
  -F "file=@release-notes.pdf"
```

Response `201`:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "filename": "DOC-CA114A84AE60.pdf",
  "original_filename": "release-notes.pdf",
  "source_type": "pdf",
  "status": "uploaded",
  "file_size_bytes": 123456
}
```

Storage behavior:

- The uploaded file is stored locally under `storage/uploads/...`.
- Postgres stores the document metadata and local `file_path`.

### GET `/documents`

Lists uploaded documents.

Response:

```json
[
  {
    "document_id": "DOC-CA114A84AE60",
    "filename": "DOC-CA114A84AE60.pdf",
    "original_filename": "release-notes.pdf",
    "source_type": "pdf",
    "status": "rules_extracted",
    "file_size_bytes": 123456,
    "file_path": "storage/uploads/DOC-CA114A84AE60.pdf",
    "content_type": "application/pdf",
    "uploaded_at": "2026-06-20T05:45:00Z",
    "updated_at": "2026-06-20T05:46:00Z",
    "metadata_json": {}
  }
]
```

### GET `/documents/{document_id}`

Gets one document by ID.

### POST `/documents/{document_id}/profile`

Profiles document pages and selects recommended extraction methods.

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "profiles": [
    {
      "page_number": 1,
      "page_type": "release_notes",
      "recommended_extractor": "docling",
      "confidence": 0.95,
      "reason": "Detected structured release notes",
      "signals_json": {}
    }
  ]
}
```

### GET `/documents/{document_id}/profile`

Returns stored profile rows for a document.

### POST `/documents/{document_id}/extract`

Runs profile if needed, extracts document content, creates semantic chunks, saves chunks to Postgres, and writes local chunk exports.

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "status": "extracted",
  "chunks_created": 66,
  "chunks_rejected": 0,
  "chunks_deduplicated": 0,
  "methods_used": ["docling"],
  "preferred_parser": "docling",
  "parser_used": "docling",
  "source_chunker": "compatiq_semantic_chunker",
  "semantic_zone_summary": {
    "requirements": 30
  },
  "llm_usage_summary": {
    "rule_extraction": 38,
    "evidence_only": 10
  },
  "rule_likelihood_summary": {
    "high": 20,
    "medium": 12,
    "low": 34
  },
  "llm_input_chunk_count": 38,
  "llm_rule_extraction_chunk_count": 38,
  "warnings": []
}
```

Persistence details:

- Chunks are saved in Postgres table `document_chunks`.
- Existing chunks for the document are replaced during extraction.
- Existing rule candidates for the document are also deleted during re-extraction because they reference old chunk IDs and would otherwise point to stale evidence.
- Local exports are written after DB save from the saved chunk records, so they include DB `chunk_id` values.
- Main local files are:
  - `storage/exports/{document_id}/chunks.json`
  - `storage/exports/{document_id}/llm_input_chunks.json`
  - `storage/exports/{document_id}/chunks.csv`
  - `storage/exports/{document_id}/document_blocks.json`
  - `storage/exports/{document_id}/document_sections.json`
  - `storage/exports/{document_id}/llm_context_pack.json`

### GET `/documents/{document_id}/chunks`

Lists chunks for a document.

Query params:

```text
send_to_llm: boolean optional
rule_likelihood: high | medium | low optional
chunk_type: string optional
llm_usage: rule_extraction | evidence_only | background_context | ignore optional
semantic_zone: string optional
```

Recommended frontend calls:

```text
GET /documents/{document_id}/chunks?send_to_llm=true
GET /documents/{document_id}/chunks?llm_usage=rule_extraction
```

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "chunks": [
    {
      "chunk_id": 321,
      "document_id": "DOC-CA114A84AE60",
      "page_number": 1,
      "chunk_index": 0,
      "chunk_type": "minimum_version_requirement",
      "section_title": "Compatibility Requirements",
      "text": "System BIOS 6.4.2 requires System Firmware 8.2.0 or later.",
      "source_excerpt": "System BIOS 6.4.2 requires System Firmware 8.2.0 or later.",
      "extraction_method": "docling",
      "quality_score": 0.95,
      "rule_likelihood": "high",
      "send_to_llm": true,
      "llm_usage": "rule_extraction",
      "rule_signal_score": 8,
      "token_estimate": 16,
      "character_count": 70,
      "metadata_json": {},
      "created_at": "2026-06-20T05:45:00Z"
    }
  ]
}
```

### GET `/chunks/{chunk_id}`

Gets one chunk by numeric DB `chunk_id`.

## Rule Extraction And Normalization

### POST `/documents/{document_id}/extract-rules`

Extracts rule candidates from chunks. If chunks do not exist, extraction is run first.

Query params:

```text
normalize=true
```

Recommended frontend call:

```text
POST /documents/{document_id}/extract-rules?normalize=true
```

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "rule_candidates_created": 55,
  "normalization_status": "normalized",
  "warnings": []
}
```

Side effects:

- Creates rows in Postgres table `rule_candidates`.
- If `normalize=true`, fills `normalized_rule_json`.
- Writes:
  - `storage/exports/{document_id}/raw_rule_candidates.json`
  - `storage/exports/{document_id}/normalized_rule_candidates.json`
- Updates document status to `rules_extracted`.

### POST `/documents/{document_id}/normalize-rule-candidates`

Normalizes all existing rule candidates for a document.

Use this if candidates were extracted with `normalize=false`, or if normalization logic changed.

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "rule_candidates": []
}
```

### GET `/documents/{document_id}/rule-candidates`

Lists candidates for one document.

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "rule_candidates": [
    {
      "candidate_id": 72,
      "document_id": "DOC-CA114A84AE60",
      "source_chunk_id": 324,
      "rule_id": null,
      "rule_type": "min_version_constraint",
      "condition_logic": "AND",
      "conditions_json": [],
      "requirement_json": {},
      "severity": "critical",
      "confidence_score": 1.0,
      "confidence_reason": "explicitly stated in source text",
      "explanation": null,
      "source_excerpt": "Customers upgrading to Enterprise OS 2026.1...",
      "review_status": "pending_review",
      "normalization_status": "normalized",
      "raw_llm_output_json": {},
      "normalized_rule_json": {},
      "validation_errors_json": null,
      "created_at": "2026-06-20T05:45:39Z",
      "updated_at": "2026-06-20T05:45:39Z"
    }
  ]
}
```

Frontend display guidance:

- Use `candidate_id` as the stable DB key for selection.
- Use `source_chunk_id` to fetch the source chunk and show evidence.
- Use `normalized_rule_json` for the structured rule preview.
- Use `source_excerpt` for compact evidence display.
- Treat `review_status=needs_clarification` as requiring manual attention before approval.

### GET `/rule-candidates`

Lists all rule candidates across all documents.

Useful for admin dashboards; avoid as the default document detail call.

### GET `/rule-candidates/{candidate_id}`

Gets one rule candidate.

### POST `/rule-candidates/{candidate_id}/normalize`

Normalizes one rule candidate.

## Full Pipeline

### POST `/documents/{document_id}/run-docintel-pipeline`

Runs the full document intelligence flow:

```text
profile -> extract chunks -> extract rules -> normalize -> write exports
```

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "status": "rules_extracted",
  "profile_count": 1,
  "extractors_used": ["docling"],
  "chunks_created": 66,
  "raw_rule_candidates_created": 55,
  "rule_candidates_created": 55,
  "normalized_rule_candidates_created": 55,
  "normalized_candidates": 52,
  "needs_human_review": 3,
  "failed_candidates": 0,
  "exports": {
    "chunks": "storage/exports/DOC-CA114A84AE60/chunks.json",
    "normalized_rule_candidates": "storage/exports/DOC-CA114A84AE60/normalized_rule_candidates.json"
  },
  "warnings": []
}
```

Recommended frontend use:

- Use this endpoint for a simple "Process Document" action.
- Use the individual endpoints when the UI needs progress per stage.

## Exports

### GET `/documents/{document_id}/exports`

Returns local export file availability.

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "exports": {
    "chunks": {
      "path": "storage/exports/DOC-CA114A84AE60/chunks.json",
      "exists": true
    },
    "normalized_rule_candidates": {
      "path": "storage/exports/DOC-CA114A84AE60/normalized_rule_candidates.json",
      "exists": true
    }
  }
}
```

### GET `/export/document/{document_id}/rule-candidates`

Exports normalized rule candidates that currently have `review_status=pending_review`.

Response:

```json
{
  "document_id": "DOC-CA114A84AE60",
  "export_type": "normalized_rule_candidates",
  "rule_candidates": []
}
```

Important: despite the name, this endpoint currently filters for `pending_review`, not `approved`.

## Approval Gap

The schema supports approval-oriented statuses, but the backend currently has no endpoint like:

```text
PATCH /api/rule-candidates/{candidate_id}/review
```

Needed request shape for frontend approval work:

```json
{
  "review_status": "approved",
  "normalized_rule_json": {},
  "review_notes": "Optional human reviewer note"
}
```

Until that endpoint exists:

- The frontend can show review controls as disabled or local-only.
- The frontend should not assume `approved`, `rejected`, or `edited` can be persisted.
- Export currently returns `pending_review` normalized candidates, not approved candidates.

## Recommended Frontend Integration Sequence

### Simple Mode

```text
POST /documents/upload
POST /documents/{document_id}/run-docintel-pipeline
GET  /documents/{document_id}/rule-candidates
GET  /documents/{document_id}/exports
```

### Stepwise Mode

```text
POST /documents/upload
POST /documents/{document_id}/profile
POST /documents/{document_id}/extract
GET  /documents/{document_id}/chunks?send_to_llm=true
POST /documents/{document_id}/extract-rules?normalize=true
GET  /documents/{document_id}/rule-candidates
GET  /export/document/{document_id}/rule-candidates
```

## Frontend Notes

- Use document `status` to show progress, but individual endpoint responses are more reliable for stage counts.
- Use `warnings` arrays directly in the UI after extract/rule-extract/pipeline calls.
- `chunks.json` and `normalized_rule_candidates.json` are local debug/export snapshots; Postgres is the source of truth for the API.
- Re-running extraction replaces chunks for the document.
- Re-running extraction also clears existing rule candidates and rule-candidate export snapshots for that document.
- Re-running rule extraction can create additional rule candidate rows unless cleanup/deduplication is added around rule candidates.
