# Frontend Route Map

Current branch: `Dharani-dev`

The frontend is a Vite React single-page app in `client/`. It does not use React Router. Navigation is controlled by local React state in `client/src/App.jsx`.

## App Shell

Primary navigation items:

| Page ID | Label | Component | Backend dependency |
| --- | --- | --- | --- |
| `Overview` | Overview | `Overview` | Health, pipeline stubs, recent activity |
| `Documents` | Documents | `Documents` | Real Document Intelligence APIs |
| `Inventory` | Inventory | `Inventory` | Placeholder `/api/devices` |
| `Compliance` | Compliance | `Compliance` | Placeholder compliance APIs |
| `Analysis` | Analysis | `Analysis` | Placeholder compliance summary |
| `Assistant` | Assistant | `Assistant` | Placeholder assistant API |
| `AuditLog` | Audit Log | `AuditLogPage` | Placeholder audit logs |

The app also includes a shared database connection modal. The modal stores the entered URL in `localStorage` and calls placeholder backend endpoints. It does not change the active SQLAlchemy database connection at runtime.

## Documents Page

`Documents` is the main working area for Document Intelligence.

Internal tabs:

| Tab | Component | Purpose | Backend status |
| --- | --- | --- | --- |
| Document Library | `DocumentLibrary` | Upload and list documents | Real upload/list APIs |
| Processing Workspace | `ProcessingWorkspace` | Run profile, extract, and rule extraction | Real step APIs |
| Review Queue | `ReviewQueue` | Inspect and review extracted candidates | Real list plus temporary review updates |
| Approved Rules Repository | `ApprovedRulesRepository` | Display approved candidates | Derived from candidate `review_status` |

Supported flow in React:

1. Upload a document through `/api/documents/upload`.
2. Select a document from the library.
3. Run processing steps through profile, extract, and extract-rules endpoints.
4. Load rule candidates.
5. Mark a candidate as approved, rejected, or needing clarification.
6. View approved candidates in the approved rules repository.

Current limitations:

- The Review Queue does not expose all chunk, export, quality, lane, and normalization warning details available from the backend.
- Approval does not promote a candidate into a durable approved-rule model.
- Rule edit is not persisted by the backend.
- Document delete and document file preview routes are not implemented by the backend.

## Overview Page

The Overview page gives a dashboard-style status view. It calls:

- `/api/pipeline/stages`
- `/api/recent-activity`
- `/api/health/services`
- `/api/pipeline/run`
- `/api/pipeline/status`

These endpoints are compatibility helpers. They are useful for keeping the merged UI alive, but they are not a full orchestration backend.

## Inventory Page

The Inventory page calls `/api/devices`. This endpoint currently returns an empty list placeholder. There is no real inventory database synchronization yet.

## Compliance Page

The Compliance page calls:

- `/api/compliance/violations`
- `/api/compliance/summary`
- `/api/compliance/scan`

These are placeholder endpoints. They do not evaluate approved rules against real devices yet.

## Analysis Page

The Analysis page calls compliance summary endpoints and displays derived dashboard analysis. Since the compliance engine is not implemented, this page currently reflects placeholder data.

## Assistant Page

The Assistant page calls `/api/assistant/query`. The backend returns a placeholder response that confirms Document Intelligence is connected but assistant reasoning over approved rules, inventory, and compliance scans is still pending.

## Audit Log Page

The Audit Log page calls `/api/audit-logs`, which currently returns an empty placeholder list.

## Route Quality Notes

- Frontend routing is simple and workable for the current merge.
- The app is currently concentrated in one large `App.jsx` file.
- Direct `fetch()` calls are spread across components.
- Several pages look production-like while their backend paths are still placeholders.

