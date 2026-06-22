# Current App Audit

Current branch: `Dharani-dev`

This audit covers the merged CompatIQ FastAPI backend and Vite React frontend as they exist now. It focuses on the application flow through Document Intelligence and the current boundary before final rule approval.

## Run Status

Previously verified after the merge:

- Backend tests: `88 passed, 1 warning`
- Frontend dependency install: `npm install` completed
- Frontend production build: `npm run build` completed
- Backend smoke: `/api/health`, `/api/health/services`, `/api/rules/candidates`, and `/api/compliance/summary` responded
- Frontend smoke: Vite app loaded from the dev server

Use these commands from the repo root:

```powershell
# Backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd client
npm install
npm run dev
```

If a stale process already owns port `8000`, start the backend on another port and set `VITE_API_BASE_URL` for the frontend:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
cd client
$env:VITE_API_BASE_URL="http://127.0.0.1:8010"
npm run dev
```

## Files Inspected

Main files reviewed:

- `app/main.py`
- `app/api/documents.py`
- `app/api/rule_candidates.py`
- `app/api/frontend_compat.py`
- `app/api/health.py`
- `app/api/export.py`
- `app/api/chunks.py`
- `client/src/App.jsx`
- `client/package.json`
- `client/vite.config.js`
- `tests/test_api_flow.py`

## Docs Created In This Audit

- `docs/CURRENT_APP_AUDIT.md`
- `docs/FRONTEND_ROUTE_MAP.md`
- `docs/API_USAGE_MAP.md`
- `docs/USER_FLOW_MAP.md`
- `docs/UI_GAP_ANALYSIS.md`
- `docs/IT_TEAM_WORKFLOW_GAP.md`

## Frontend Route Summary

The frontend is a single-page React app. Navigation is state-based, not URL-router-based.

Primary pages:

- Overview
- Documents
- Inventory
- Compliance
- Analysis
- Assistant
- Audit Log

The `Documents` page is the real Document Intelligence workflow area. It has internal tabs for document library, processing workspace, review queue, and approved rules repository.

Inventory, Compliance, Analysis, Assistant, and Audit Log are visually present but mostly backed by compatibility placeholders.

## Backend Endpoint Summary

Real backend support exists for:

- Health checks
- Document upload
- Document listing and details
- Document profiling
- Content extraction and chunking
- Rule extraction
- Rule candidate normalization
- Rule candidate listing and details
- Local export status
- Debug LLM/demo endpoints

Temporary or placeholder backend support exists for:

- Review approval/reject/clarify status updates
- Approved rules list derived from approved candidates
- Pipeline dashboard endpoints
- Inventory device list
- Compliance summary, violations, and scan
- Assistant query
- Audit logs
- Runtime database connect UI

## User Flow Summary

Current working flow:

1. User starts backend and frontend.
2. React shell checks `/api/health`.
3. User uploads a document.
4. Backend stores the document.
5. User runs profile, extraction, and rule extraction.
6. Backend creates chunks, exports, raw candidates, and normalized candidates.
7. User opens Review Queue.
8. User marks candidates approved, rejected, or needing clarification.
9. Approved Rules Repository shows candidates whose `review_status` is `approved`.

The flow currently stops at candidate review status.

## Approval Logic Status

Approval is temporary.

Current behavior:

- The candidate row gets `review_status = "approved"`.
- `/api/rules/approved` returns candidates with that status.
- No canonical approved-rule record is created.
- No knowledge graph write occurs.
- No compliance engine consumes approved rules yet.

This is acceptable as a merge bridge, but it should be visibly treated as temporary in product planning.

## Biggest Mismatches

1. The UI looks broader than the backend reality.

   Inventory, Compliance, Analysis, Assistant, and Audit Log are present but mostly placeholder-backed.

2. Approved Rules Repository is not a real repository yet.

   It is a filtered view of rule candidates.

3. Review Queue does not expose enough evidence.

   Backend exports chunks, quality reports, warnings, and normalized JSON, but React does not yet present a complete reviewer packet.

4. Some frontend actions have no backend route.

   Document delete, document file preview, and candidate edit persistence are not implemented.

5. Runtime DB connect is not real.

   The UI stores a URL and calls placeholder endpoints, but the backend database connection is not switched dynamically.

## IT Workflow Gaps

The current app is strong enough to demonstrate Document Intelligence extraction, but not enough for an IT team to run an operational compliance workflow.

Missing pieces:

- Canonical approved-rule model
- Reviewer identity and audit trail
- Source evidence packet per rule
- Inventory ingestion
- Affected-device mapping
- Compliance scan results
- Remediation actions
- Exceptions or waivers
- Rule versioning and document change tracking

## Recommended Design Brainstorming Topics

- What exact fields are required before a rule can be approved?
- Should approved rules be separate from extraction candidates?
- What evidence must be visible before approval?
- How should affected devices be shown once inventory is connected?
- Should compliance be grouped by device, rule, model, OS version, or severity?
- Should the assistant answer from unapproved candidates?
- What audit events must be immutable?
- What UI labels should distinguish real backend data from placeholders during development?

## Small Fixes Made During Merge

Small compatibility fixes already made before this audit:

- Added frontend compatibility endpoints so the React app can load.
- Added temporary rule review endpoints.
- Added frontend environment example.
- Changed frontend API paths from `/api/v1` to `/api`.
- Added tests covering review and compatibility routes.

No UI redesign, major logic rewrite, or feature removal was performed for this audit.

