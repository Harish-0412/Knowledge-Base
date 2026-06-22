# User Flow Map

Current branch: `Dharani-dev`

This file documents the current application flow from launch through Document Intelligence review, stopping just before final durable approval and compliance enforcement.

## Launch And Backend Connection

1. Start the FastAPI backend.
2. Start the Vite frontend.
3. The React shell checks `/api/health`.
4. If the backend is reachable, dashboard counts are fetched from documents, candidates, approved candidates, devices, and compliance summary endpoints.
5. If the backend is offline, the app shows an offline banner and disables backend-dependent actions.

## Document Upload

1. The user opens `Documents`.
2. The user selects `Document Library`.
3. The user uploads a document.
4. Frontend calls `POST /api/documents/upload`.
5. Backend stores the file and creates a `Document` record with status `uploaded`.
6. The document list refreshes through `GET /api/documents`.

## Document Processing

1. The user selects a document.
2. The user moves to `Processing Workspace`.
3. The frontend can call:
   - `POST /api/documents/{document_id}/profile`
   - `POST /api/documents/{document_id}/extract`
   - `POST /api/documents/{document_id}/extract-rules`
4. The backend profiles the document, extracts chunks, builds exports, and extracts normalized rule candidates.
5. The document status moves through backend states such as `profiled`, `extracted`, and `rules_extracted`.

## Candidate Review

1. The user opens `Review Queue`.
2. The frontend loads candidates through `/api/rules/candidates`, with fallback to `/api/rule-candidates`.
3. The UI displays candidate status, confidence, severity, extracted subject/predicate/object, and source excerpt.
4. The user can mark a candidate as:
   - approved
   - rejected
   - needs clarification
5. The preferred backend call is `PATCH /api/rule-candidates/{candidate_id}/review`.
6. The backend updates `review_status`.

## Approved Rules Repository

1. The user opens `Approved Rules Repository`.
2. The frontend calls `/api/rules/approved`.
3. Backend returns candidates whose `review_status` is `approved`.

This is currently a derived candidate list, not a true approved-rule repository.

## Where The Flow Stops Today

The current merged app stops at temporary review status.

Implemented:

- Document upload
- Document profiling
- Content extraction and chunking
- Rule extraction
- Rule normalization
- Candidate list and review status updates
- Local export files

Not implemented:

- Durable approved-rule promotion
- Approved rules table/model/API
- Knowledge graph write
- Inventory synchronization
- Device-rule compatibility evaluation
- Real compliance scan records
- Remediation workflow
- Audit trail of reviewer decisions

## Current Approval Logic Status

Approval is not final business approval yet.

Current behavior:

- `approved` is a value stored on `RuleCandidate.review_status`.
- `/api/rules/approved` filters candidates with that status.
- The backend response explicitly says full approved-rule promotion is pending backend integration.

Expected future behavior:

- Validated candidate is converted into a canonical approved rule.
- Approved rule is stored separately from raw extraction output.
- Rule source evidence and reviewer identity are preserved.
- Approved rule is available to compliance scanning and assistant reasoning.

