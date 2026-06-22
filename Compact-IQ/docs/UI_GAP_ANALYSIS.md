# UI Gap Analysis

Current branch: `Dharani-dev`

This analysis documents frontend gaps after the merge. It does not recommend redesigning the UI now; it identifies what should be discussed before deeper implementation.

## What Works

- The React app starts and connects to the FastAPI backend.
- The main Document Intelligence flow is visible in the Documents section.
- Document upload, processing actions, candidate review, and approved-candidate display are wired to backend endpoints.
- Offline backend handling exists.
- Compatibility endpoints prevent large parts of the UI from crashing while backend domains are still incomplete.

## Main UI And Backend Mismatches

| Area | UI implication | Backend reality |
| --- | --- | --- |
| Approved Rules Repository | Looks like a final repository | It is a filtered candidate list |
| Inventory | Looks like device inventory exists | `/api/devices` returns placeholder empty data |
| Compliance | Looks like scan engine exists | Compliance endpoints are placeholders |
| Analysis | Looks like real analysis exists | It reads placeholder compliance summary |
| Assistant | Looks like rule/device reasoning exists | Assistant endpoint returns a placeholder response |
| Audit Log | Looks like audit events exist | Audit endpoint returns an empty placeholder list |
| Database connection | Looks like runtime DB switching | Backend accepts URL but does not reconfigure DB |

## Document Intelligence Visibility Gaps

The backend exposes more diagnostic information than the React UI currently shows.

Missing or underexposed:

- Extracted chunks and chunk filters
- Source page and source chunk navigation
- Extraction method and parser details
- Processing lane summary
- LLM call count
- Deterministic vs LLM candidate count
- Candidate quality report
- Normalization warnings
- Local export status
- Raw LLM output versus normalized rule JSON
- Explicit reason why a candidate needs human review

These details are important for trust. IT users need to understand why a rule exists before approving it.

## Review Queue Gaps

- Candidate approval appears stronger than it really is.
- Rule edits are not persisted by a real backend endpoint.
- There is no reviewer identity, timestamp, comment, or decision history.
- Rejection and clarification do not create follow-up work.
- The candidate detail view does not fully expose all normalized condition and requirement fields.
- Confidence score is visible, but confidence reason and quality warnings are not always prominent.

## Frontend Engineering Gaps

- `client/src/App.jsx` is very large and contains routing, data fetching, page components, UI primitives, and domain logic.
- `API_BASE` is duplicated.
- `fetch()` calls are direct and inconsistent.
- There is no shared loading/error pattern per backend domain.
- Several fallbacks hide missing backend functionality.
- Placeholder endpoints make UI testing easy, but can also make unfinished features look complete.

## Low-Risk Small Fixes To Consider

These are small implementation topics for later, not mandatory before brainstorming:

- Centralize API base URL and fetch helpers.
- Add visible labels for temporary backend domains.
- Disable or annotate final approval actions until approved-rule promotion exists.
- Surface candidate quality warnings in the Review Queue.
- Add a document-specific processing summary panel from `extract-rules` response fields.
- Add backend routes or remove UI affordances for document delete and file preview.

