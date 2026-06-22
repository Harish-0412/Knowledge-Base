# CompatIQ Document Intelligence Service

FastAPI-first backend for the CompatIQ Member 3 Document Intelligence Engine, including the React frontend UI.

The service supports document upload, profiling, extraction, chunking, rule candidate extraction, deterministic normalization, local JSON exports, and the **new Tiered Human Rule Review UI**.

See [EXTRA_FEATURES_README.md](EXTRA_FEATURES_README.md) for Firebase authentication, dashboard routing, live NVD CVE enrichment, and the searchable Compatibility Rulebook.

## 🚀 Quick Start for Teammates

### 1. Start the Database (PostgreSQL)
```powershell
docker compose up -d
python scripts/create_tables.py
```

### 2. Start the Backend (FastAPI)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```
*API runs at http://127.0.0.1:8000*

### 3. Start the Frontend (Vite + React)
Open a new terminal:
```powershell
cd client
npm install
npm run dev
```
*UI runs at http://localhost:5173*

---

## Repository Layout

This branch combines the local FastAPI backend with the React frontend from `origin/Dharani-dev`.

```text
app/              FastAPI backend package
scripts/          Backend utility scripts
tests/            Backend tests
streamlit_app/    Backend debug Streamlit UI
client/           Vite React frontend
docs/             Shared project/reference documentation
schemas/          Shared source-of-truth JSON schemas
```

The backend currently remains at the repository root to avoid breaking imports and tests. The frontend is kept as a separate module under `client/`.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` if you want to override local settings.

The development database target is PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://compatiq:compatiq@localhost:55432/compatiq_docintel
```

Tests use SQLite only so they can run even when local PostgreSQL is not available.
The Docker compose file maps PostgreSQL to host port `55432` to avoid conflicts with native Postgres installations that often use `5432`.

## Run the Backend

```powershell
uvicorn app.main:app --reload
```

Swagger UI is available at `http://127.0.0.1:8000/docs`.

## Run the Frontend

The frontend is a Vite React app in `client/`.

```powershell
cd client
npm run dev
```

By default the frontend should call:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Create `client/.env.local` if you need a different backend URL, for example `http://127.0.0.1:8001`.

## Combined Local Run

```powershell
docker compose up -d
python scripts/create_tables.py
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd client
npm run dev
```

Backend health should be available at `http://127.0.0.1:8000/api/health`.

## PostgreSQL

```powershell
docker compose up -d
python scripts/create_tables.py
```

The database health endpoint runs `SELECT 1` against the configured database:

```powershell
curl http://127.0.0.1:8000/api/health/db
```

## Upload Documents

Accepted file types in Phase 2:

- `.pdf`
- `.txt`
- `.md`
- `.csv`
- `.docx`

Upload with curl:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/upload" `
  -F "file=@examples/mock_release_notes.txt"
```

List uploaded documents:

```powershell
curl http://127.0.0.1:8000/api/documents
```

Get one document:

```powershell
curl http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME
```

## Profile Documents

Create or replace a document profile:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/profile"
```

Read the current profile:

```powershell
curl http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/profile
```

Example response:

```json
{
  "document_id": "DOC-ABC123",
  "profiles": [
    {
      "page_number": 1,
      "page_type": "text",
      "recommended_extractor": "text",
      "confidence": 0.95,
      "reason": "Plain text document"
    }
  ]
}
```

Profiling updates the document status to `profiled` and records a `profile` extraction job. Re-running profiling replaces previous profile rows for the document.

## Extract and Chunk Documents

Extract content and store chunks:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/extract"
```

Example response:

```json
{
  "document_id": "DOC-ABC123",
  "status": "extracted",
  "chunks_created": 8,
  "chunks_rejected": 2,
  "chunks_deduplicated": 1,
  "methods_used": ["text"],
  "rule_likelihood_summary": {
    "high": 3,
    "medium": 1,
    "low": 4
  },
  "llm_input_chunk_count": 4,
  "warnings": []
}
```

Read all chunks for a document:

```powershell
curl http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/chunks
```

Filter chunks for LLM input or review:

```powershell
curl "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/chunks?send_to_llm=true"
curl "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/chunks?rule_likelihood=high"
curl "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/chunks?chunk_type=requirement_rule"
```

Read one chunk:

```powershell
curl http://127.0.0.1:8000/api/chunks/1
```

If a document has not been profiled yet, extraction automatically runs profiling first. Re-running extraction replaces existing chunks for the document.

## How Intelligent Chunking Works

The extraction layer is now Docling-preferred and structure-aware. Docling is used as the preferred parser for structured documents when enabled; PyMuPDF, Chandra OCR, TXT/MD, and CSV paths are fallbacks or direct parsers. All parser output is normalized into CompatIQ semantic chunks before storage.

- Metadata grouping: title, document ID, release version, release date, document type, vendor, platform, and applies-to lines become one `document_metadata` chunk.
- Section grouping: headings are stored as `section_title`; section body text is kept in the chunk text instead of creating heading-only chunks.
- Rule-bearing detection: sentences with terms like `requires`, `minimum`, `or later`, `not supported`, `incompatible`, `fixed`, `BIOS`, `firmware`, `driver`, or `OS` get higher rule likelihood.
- Table row chunking: CSV/table rows preserve headers, e.g. `Model: R420 | OS: ESXi 5.1.x | Required BIOS: 02.04.02`.
- `rule_likelihood`: `high`, `medium`, or `low` based on deterministic scoring.
- `llm_usage`: `global_context`, `background_context`, `rule_extraction`, `evidence_only`, or `ignore`.
- `send_to_llm`: kept for backward compatibility and derived from `llm_usage=rule_extraction`.
- Deduplication: duplicate normalized text is collapsed before storage, preferring the selected extractor or higher-priority extraction method.
- Local exports: extraction writes Docling/debug files, `document_blocks.json`, `document_sections.json`, `chunks.json`, `chunks.csv`, `llm_context_pack.json`, and `llm_input_chunks.json`.

Useful config:

```env
PREFERRED_PARSER=docling
DOCLING_ENABLED=false
DOCLING_TABLE_STRUCTURE=true
DOCLING_TABLE_MODE=accurate
DOCLING_OCR_ENABLED=false
CHANDRA_OCR_ENABLED=false
PYMUPDF_FALLBACK_ENABLED=true
DEBUG_EXTRACTOR_COMPARISON=false
SEND_MEDIUM_LIKELIHOOD_CHUNKS=true
DEBUG_STORE_REJECTED_CHUNKS=false
CHUNKER_MODE=docling_hybrid_plus_compatiq
HYBRID_CHUNKER_MAX_TOKENS=800
```

Manual chunking check:

```powershell
docker compose up -d
python scripts/create_tables.py
uvicorn app.main:app --reload
```

Then upload a document, run:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/run-docintel-pipeline"
curl.exe "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/chunks"
curl.exe "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/chunks?send_to_llm=true"
```

Check local files:

```text
storage/exports/{document_id}/chunks.json
storage/exports/{document_id}/chunks.csv
storage/exports/{document_id}/document_blocks.json
storage/exports/{document_id}/document_sections.json
storage/exports/{document_id}/llm_context_pack.json
storage/exports/{document_id}/llm_input_chunks.json
```

Before/after example:

```text
Before:
Release Version
6.4.2
15 June 2026
## 1. Overview

After:
chunk_type=document_metadata
text=Release Version: 6.4.2

chunk_type=overview
section_title=1. Overview
text=ACME Platform Release 6.4.2 introduces...
```

Docling debug exports, when available:

```text
storage/exports/{document_id}/docling_document.json
storage/exports/{document_id}/docling_markdown.md
storage/exports/{document_id}/docling_hybrid_chunks.json
```

If Docling is not used for a run, placeholder files are written with clear warnings so the export contract stays stable.

## LLM Adapter

Mock mode is the safest local/demo setting and does not call Ollama:

```env
USE_MOCK_LLM=true
ALLOW_MOCK_LLM_RULE_EXTRACTION=true
OLLAMA_MODEL=gemma4:31b
```

For manual rule extraction, keep `ALLOW_MOCK_LLM_RULE_EXTRACTION=false` unless you intentionally want demo/test candidates. With mock rule extraction disabled, the API returns a clear error instead of silently producing mock candidates.

Test the configured adapter:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/debug/llm-test" `
  -H "Content-Type: application/json" `
  -d "{\"prompt\":\"Extract one compatibility rule from: Windows Server 2012 requires BIOS 1.3.5 or later.\"}"
```

Example response in mock mode:

```json
{
  "provider": "mock",
  "model": "gemma4:31b",
  "ok": true,
  "result": {
    "rule_candidates": [
      {
        "review_status": "pending_review"
      }
    ]
  }
}
```

Configure Ollama Cloud by disabling mock mode and setting the endpoint values:

```env
USE_MOCK_LLM=false
ALLOW_MOCK_LLM_RULE_EXTRACTION=false
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_GENERATE_PATH=/api/generate
OLLAMA_API_KEY=your-key-here
OLLAMA_MODEL=gemma4:31b
OLLAMA_TIMEOUT_SECONDS=180
```

Use `gemma4:12b` or `gemma4:26b` instead if those Gemma 4 models are exposed by your Ollama Cloud account. The current verified Cloud model for this setup is `gemma4:31b`.

LLM health:

```powershell
curl http://127.0.0.1:8000/api/health/llm
curl "http://127.0.0.1:8000/api/health/llm?deep=true"
```

Without `deep=true`, real mode only checks that configuration is present. With `deep=true`, the service performs a lightweight generation call. If Ollama Cloud fails, verify `OLLAMA_BASE_URL`, `OLLAMA_GENERATE_PATH`, credentials, model name, and timeout. Error responses intentionally avoid exposing secrets.

This service is configured for direct Ollama Cloud API calls, not local Ollama model hosting.

## Extract Raw Rule Candidates

Rule extraction reads stored chunks, filters likely rule-bearing chunks, calls the configured LLM adapter, repairs simple JSON formatting problems, and stores raw candidates for human review.

If a document has not been extracted yet, this endpoint auto-runs profiling and extraction first:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/extract-rules"
```

Example response:

```json
{
  "document_id": "DOC-ABC123",
  "rule_candidates_created": 3,
  "normalization_status": "pending",
  "warnings": []
}
```

Read candidates for one document:

```powershell
curl http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/rule-candidates
```

Read all candidates:

```powershell
curl http://127.0.0.1:8000/api/rule-candidates
```

Read one candidate:

```powershell
curl http://127.0.0.1:8000/api/rule-candidates/1
```

Phase 6 stores raw candidates only. Every candidate remains `pending_review` and `pending_normalization`.

## Normalize Rule Candidates

By default, rule extraction now normalizes candidates immediately for demo friendliness:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/extract-rules"
```

Skip automatic normalization:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/extract-rules?normalize=false"
```

Normalize one candidate:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/rule-candidates/1/normalize"
```

Normalize all candidates for a document:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/normalize-rule-candidates"
```

The normalizer maps aliases for component types, operators, rule types, severity, and versions. Raw values are preserved in `value_raw`, `version_raw`, `source_excerpt`, and `raw_llm_output_json`.

Sample normalized output:

```json
{
  "candidate_id": "RCAND-000001",
  "rule_type": "min_version_constraint",
  "condition_logic": "AND",
  "conditions": [
    {
      "condition_id": "COND-001",
      "component_type": "cpu",
      "component_name": "Intel Xeon",
      "component_family": "E5-2400 V2",
      "operator": "installed",
      "value_raw": "Intel Xeon E5-2400 V2 family",
      "value_normalized": "intel_xeon_e5_2400_v2_family"
    }
  ],
  "requirements": [
    {
      "requirement_id": "REQ-001",
      "component_type": "bios",
      "component_name": "System BIOS",
      "operator": ">=",
      "version_raw": "02.00.21",
      "version_normalized": "2.0.21",
      "version_scheme": "semantic",
      "requirement_kind": "min_version"
    }
  ],
  "review_status": "pending_review"
}
```

## Full Demo Pipeline

Run the complete Member 3 document intelligence flow after upload:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/run-docintel-pipeline"
```

This runs:

```text
profile -> extract chunks -> extract rule candidates -> normalize candidates
```

Example response:

```json
{
  "document_id": "DOC-ABC123",
  "status": "rules_extracted",
  "profile_count": 1,
  "extractors_used": ["text"],
  "chunks_created": 2,
  "raw_rule_candidates_created": 1,
  "rule_candidates_created": 1,
  "normalized_rule_candidates_created": 1,
  "normalized_candidates": 1,
  "needs_human_review": 0,
  "failed_candidates": 0,
  "exports": {
    "profile": "storage/exports/DOC-ABC123/profile.json",
    "docling_document": "storage/exports/DOC-ABC123/docling_document.json",
    "docling_markdown": "storage/exports/DOC-ABC123/docling_markdown.md",
    "docling_hybrid_chunks": "storage/exports/DOC-ABC123/docling_hybrid_chunks.json",
    "document_blocks": "storage/exports/DOC-ABC123/document_blocks.json",
    "document_sections": "storage/exports/DOC-ABC123/document_sections.json",
    "chunks": "storage/exports/DOC-ABC123/chunks.json",
    "chunks_csv": "storage/exports/DOC-ABC123/chunks.csv",
    "llm_context_pack": "storage/exports/DOC-ABC123/llm_context_pack.json",
    "llm_input_chunks": "storage/exports/DOC-ABC123/llm_input_chunks.json",
    "raw_rule_candidates": "storage/exports/DOC-ABC123/raw_rule_candidates.json",
    "normalized_rule_candidates": "storage/exports/DOC-ABC123/normalized_rule_candidates.json",
    "pipeline_summary": "storage/exports/DOC-ABC123/pipeline_summary.json"
  },
  "warnings": []
}
```

Run the built-in demo document:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/debug/run-demo-document"
```

Swagger demo flow:

1. Open `http://127.0.0.1:8000/docs`.
2. Use `POST /api/documents/upload` with a `.txt`, `.md`, `.csv`, `.pdf`, or `.docx` file.
3. Copy the returned `document_id`.
4. Run `POST /api/documents/{document_id}/run-docintel-pipeline`.
5. Inspect `GET /api/documents/{document_id}/chunks`.
6. Inspect `GET /api/documents/{document_id}/rule-candidates`.
7. Inspect `GET /api/documents/{document_id}/exports`.

Swagger UI is available at `http://127.0.0.1:8000/docs`. Use the `documents` section to upload files and inspect responses from the browser.

## Local JSON Exports

PostgreSQL remains the source of truth. For demo, debugging, and teammate handoff, the pipeline also writes local JSON files under:

```text
storage/exports/{document_id}/
```

Files written by the pipeline:

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

Check export status:

```powershell
curl http://127.0.0.1:8000/api/documents/DOC-REPLACE_ME/exports
```

Member integration export:

```powershell
curl http://127.0.0.1:8000/api/export/document/DOC-REPLACE_ME/rule-candidates
```

## Manual End-to-End Test

```powershell
docker compose up -d
python scripts/create_tables.py
uvicorn app.main:app --reload
```

In another terminal:

```powershell
$upload = curl.exe -s -X POST "http://127.0.0.1:8000/api/documents/upload" -F "file=@examples/mock_release_notes.txt"
$doc = ($upload | ConvertFrom-Json).document_id
curl.exe -X POST "http://127.0.0.1:8000/api/documents/$doc/run-docintel-pipeline"
curl.exe "http://127.0.0.1:8000/api/documents/$doc/exports"
curl.exe "http://127.0.0.1:8000/api/export/document/$doc/rule-candidates"
```

Expected result: status is `rules_extracted`, chunks and normalized rule candidates exist, and export files exist in `storage/exports/{document_id}/`.

## Streamlit Integration Later

A Streamlit UI can call the FastAPI endpoints directly:

- Upload: `POST /api/documents/upload`
- Run pipeline: `POST /api/documents/{document_id}/run-docintel-pipeline`
- Show chunks: `GET /api/documents/{document_id}/chunks`
- Show candidates: `GET /api/documents/{document_id}/rule-candidates`
- Show local export status: `GET /api/documents/{document_id}/exports`
- Download teammate contract JSON: `GET /api/export/document/{document_id}/rule-candidates`

The UI should treat `normalized_rule_json`, `review_status`, `normalization_status`, `source_chunk_id`, and `source_excerpt` as the key review fields.

## Handoff Notes

This service owns Member 3 Document Intelligence:

- Document upload metadata and file storage.
- Document profiling and extraction routing.
- Chunk creation with source evidence.
- Raw LLM rule candidate extraction.
- Deterministic normalization and validation for human review.
- Export of normalized rule candidates.
- Local JSON export snapshots for demo and debugging.

This service does not own:

- Rule approval.
- Compliance scans.
- Neo4j graph construction.
- Final violation generation.
- Inventory ingestion.

Member 1 can use the PostgreSQL output in `rule_candidates`, especially `normalized_rule_json`, `review_status`, `normalization_status`, `document_id`, and `source_chunk_id`.

Member 5 can integrate through:

```powershell
POST /api/documents/upload
POST /api/documents/{document_id}/run-docintel-pipeline
GET  /api/documents/{document_id}/exports
GET  /api/export/document/{document_id}/rule-candidates
```

Member 2 should consume approved rules later, not raw candidates. Phase 9 still produces candidates for human review only.

Mock LLM mode:

```env
USE_MOCK_LLM=true
```

Ollama Cloud mode:

```env
USE_MOCK_LLM=false
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_GENERATE_PATH=/api/generate
OLLAMA_API_KEY=your-key-here
OLLAMA_MODEL=gemma4:31b
```

## Optional Docling and Chandra OCR

The stable extraction paths remain TXT/MD, CSV, and selectable-text PDFs through PyMuPDF. Optional integrations can be enabled without changing the API:

```env
ENABLE_DOCLING=true
ENABLE_CHANDRA_OCR=true
CHANDRA_API_URL=https://your-ocr-service/extract
CHANDRA_TIMEOUT_SECONDS=120
```

Docling is used only when installed and enabled. It attempts layout-aware extraction and returns markdown/text blocks that preserve headings and tables where Docling exposes them.

Chandra OCR is used only when enabled and configured with `CHANDRA_API_URL`. It sends the uploaded document bytes to that OCR API and expects a JSON response with page text and confidence.

If either dependency is disabled, missing, or misconfigured, the service returns a clear extractor error and does not break TXT/CSV/PyMuPDF paths.

## Run Tests

```powershell
pytest
```

## Phase Status

- Phase 1: complete
- Phase 2: complete
- Phase 3: complete
- Phase 4: complete
- Phase 5: complete
- Phase 6: complete
- Phase 7: complete
- Phase 8: complete
- Phase 9: complete
- Document upload: complete
- Document profiling: complete
- Extraction and chunking: complete for TXT/MD/CSV and clean PyMuPDF PDFs
- LLM adapter: complete for mock mode and Ollama Cloud boundary
- Raw rule extraction: complete
- Normalization and validation: complete
- Full demo pipeline endpoint: complete
- Handoff/export contract: complete
- Tiered Human Rule Review UI (Auto/Batch/Individual): complete
- Optional Docling/Chandra adapter integration: complete with mocked tests
- Compliance scanning: not started
