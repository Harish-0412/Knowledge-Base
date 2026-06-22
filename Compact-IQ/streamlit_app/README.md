# CompatIQ Member 3 Streamlit Tester

Developer-only Streamlit UI for manually testing the FastAPI Document Intelligence pipeline.

This app does not implement backend logic. It only calls FastAPI endpoints.

## Setup

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,streamlit]"
```

## Backend Dependency

Start PostgreSQL and create tables:

```powershell
docker compose up -d
python scripts/create_tables.py
```

Start the FastAPI backend:

```powershell
uvicorn app.main:app --reload
```

Default backend URL:

```text
http://127.0.0.1:8000
```

## Configure FASTAPI_BASE_URL

Option 1: environment variable

```powershell
$env:FASTAPI_BASE_URL="http://127.0.0.1:8000"
```

Option 2: use the sidebar text input in the Streamlit app.

## Run Streamlit

```powershell
streamlit run streamlit_app/app.py
```

## Manual Test Flow

1. Open the Health tab and verify backend, DB, and LLM status.
2. Upload a `.txt`, `.md`, `.csv`, `.pdf`, or `.docx` document.
3. Select the returned `document_id`.
4. Run Profile and verify `recommended_extractor`.
5. Run Extraction and inspect chunks.
6. Extract Rules from Chunks and inspect raw and normalized candidate JSON.
7. Run Full Document Intelligence Pipeline for an end-to-end check.
8. Open Exports and verify local JSON snapshots exist.

## What This UI Does Not Do

- Does not connect directly to PostgreSQL.
- Does not call Ollama directly.
- Does not normalize rules locally.
- Does not approve rules.
- Does not replace production frontend work.

## Troubleshooting

- Backend unreachable: verify `uvicorn app.main:app --reload` is running and the sidebar URL is correct.
- DB health fails: run `docker compose up -d` and `python scripts/create_tables.py`.
- LLM health fails: use `USE_MOCK_LLM=true` for local testing or verify Ollama Cloud settings.
- No export files: run the full pipeline or the individual profile/extract/rule extraction steps first.
- DOCX/PDF failures: DOCX, Docling, Chandra OCR, and scanned PDFs depend on optional backend configuration.
