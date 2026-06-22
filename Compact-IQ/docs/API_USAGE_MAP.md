# API Usage Map

Current branch: `Dharani-dev`

This map records how the React frontend currently calls the FastAPI backend after the merge. It separates real Document Intelligence endpoints from compatibility aliases and temporary placeholder endpoints.

## Backend API Surface

The backend mounts all routers under `/api` from `app/main.py`.

### Health

| Method | Endpoint | Status | Used By |
| --- | --- | --- | --- |
| `GET` | `/api/health` | Real | App shell backend status |
| `GET` | `/api/health/db` | Real | Not currently used by React |
| `GET` | `/api/health/llm` | Real | Not currently used by React |
| `GET` | `/api/health/services` | Compatibility summary | Overview |

### Document Intelligence

| Method | Endpoint | Status | Used By |
| --- | --- | --- | --- |
| `POST` | `/api/documents/upload` | Real | Documents upload |
| `GET` | `/api/documents` | Real | App metrics, Documents |
| `GET` | `/api/documents/{document_id}` | Real | Available, not central in UI |
| `POST` | `/api/documents/{document_id}/profile` | Real | Documents processing |
| `GET` | `/api/documents/{document_id}/profile` | Real | Available, not central in UI |
| `POST` | `/api/documents/{document_id}/extract` | Real | Documents processing |
| `GET` | `/api/documents/{document_id}/chunks` | Real | Available, not surfaced in React |
| `GET` | `/api/documents/{document_id}/exports` | Real | Available, not surfaced in React |
| `POST` | `/api/documents/{document_id}/extract-rules` | Real | Documents processing |
| `POST` | `/api/documents/{document_id}/normalize-rule-candidates` | Real | Available, not central in UI |
| `GET` | `/api/documents/{document_id}/rule-candidates` | Real | Available, not central in UI |
| `POST` | `/api/documents/{document_id}/run-docintel-pipeline` | Real | Available, UI mostly calls individual steps |
| `POST` | `/api/documents/{document_id}/process` | Compatibility stub | Fallback in Documents |

### Rule Candidates

| Method | Endpoint | Status | Used By |
| --- | --- | --- | --- |
| `GET` | `/api/rule-candidates` | Real | Fallback list |
| `GET` | `/api/rule-candidates/{candidate_id}` | Real | Available |
| `POST` | `/api/rule-candidates/{candidate_id}/normalize` | Real | Available |
| `PATCH` | `/api/rule-candidates/{candidate_id}/review` | Temporary review update | Review Queue |
| `POST` | `/api/rule-candidates/{candidate_id}/approve` | Temporary review update | Available |
| `POST` | `/api/rule-candidates/{candidate_id}/reject` | Temporary review update | Available |
| `POST` | `/api/rule-candidates/{candidate_id}/clarify` | Temporary review update | Available |
| `GET` | `/api/rules/candidates` | Compatibility alias | Main candidate list |
| `GET` | `/api/rules/candidates/{candidate_id}` | Compatibility alias | Available |
| `POST` | `/api/rules/candidates/{candidate_id}/approve` | Compatibility alias | Fallback |
| `POST` | `/api/rules/candidates/{candidate_id}/reject` | Compatibility alias | Fallback |
| `POST` | `/api/rules/candidates/{candidate_id}/clarify` | Compatibility alias | Fallback |
| `GET` | `/api/rules/approved` | Compatibility derived list | Approved Rules page, metrics |

Approval note: candidate approval currently changes `review_status` only. It does not create a durable approved-rule entity, write to Neo4j, or trigger compliance analysis.

### Export And Debug

| Method | Endpoint | Status | Used By |
| --- | --- | --- | --- |
| `GET` | `/api/export/document/{document_id}/rule-candidates` | Real | Available, not central in React |
| `GET` | `/api/chunks/{chunk_id}` | Real | Available, not central in React |
| `POST` | `/api/debug/llm-test` | Real debug | Developer use |
| `POST` | `/api/debug/run-demo-document` | Real debug | Developer use |

### Inventory, Compliance, Assistant, Audit

| Method | Endpoint | Status | Used By |
| --- | --- | --- | --- |
| `POST` | `/api/database/connect` | Placeholder | App data connection modal |
| `POST` | `/api/inventory/connect-db` | Placeholder | App data connection modal |
| `GET` | `/api/devices` | Placeholder empty list | Inventory, metrics |
| `GET` | `/api/compliance/summary` | Placeholder | Compliance, Analysis, metrics |
| `GET` | `/api/compliance/scans/latest` | Placeholder alias | Fallback |
| `GET` | `/api/compliance/scans/SCAN-000001` | Placeholder alias | Fallback |
| `GET` | `/api/compliance/violations` | Placeholder empty list | Compliance |
| `GET` | `/api/compliance/scans/latest/violations` | Placeholder alias | Fallback |
| `GET` | `/api/compliance/scans/SCAN-000001/violations` | Placeholder alias | Fallback |
| `POST` | `/api/compliance/scan` | Placeholder | Compliance scan button |
| `POST` | `/api/assistant/query` | Placeholder | Assistant |
| `GET` | `/api/audit-logs` | Placeholder empty list | Audit Log |
| `GET` | `/api/recent-activity` | Compatibility summary from documents | Overview |
| `GET` | `/api/pipeline/stages` | Compatibility status list | Overview |
| `POST` | `/api/pipeline/run` | Placeholder | Overview |
| `GET` | `/api/pipeline/status` | Placeholder | Overview |

## Frontend Fetch Patterns

`client/src/App.jsx` calls the backend directly from page components. `API_BASE` is duplicated in multiple component scopes as:

```js
import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
```

There is no central API client, response normalizer, request timeout helper, or shared error mapper yet.

## Missing Or Mismatched Calls

| Frontend call | Backend status | Current behavior |
| --- | --- | --- |
| `POST /api/documents` | Not implemented | Upload fallback can fail |
| `DELETE /api/documents/{document_id}` | Not implemented | Delete is not backed by API |
| `PATCH /api/rules/candidates/{id}` | Not implemented | Rule edit is local-only/fallback warning |
| `/api/documents/{document_id}/view` | Not implemented | Open/view action has no backend route |
| `/api/documents/{document_id}/file` | Not implemented | File action has no backend route |

