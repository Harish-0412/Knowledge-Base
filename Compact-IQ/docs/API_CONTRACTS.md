# API_CONTRACTS — CompatIQ

Base path: `/api/v1`

## Documents

### POST `/documents/upload`
Uploads a source document.

Response:
```json
{
  "document_id": "DOC-000001",
  "filename": "R420_BIOS_Release_Notes.pdf",
  "source_type": "pdf",
  "document_status": "uploaded"
}
```

### POST `/documents/{document_id}/profile`
Profiles pages and recommends extraction methods.

### POST `/documents/{document_id}/extract`
Runs extraction router and stores chunks.

### GET `/documents/{document_id}/chunks`
Returns stored chunks.

## Rule Extraction

### POST `/documents/{document_id}/extract-rules`
Runs LLM extraction over chunks and creates rule candidates.

### GET `/rule-candidates`
Lists rule candidates.

### GET `/rule-candidates/{candidate_id}`
Returns one candidate with source evidence.

### PATCH `/rule-candidates/{candidate_id}/review`
Approve, edit, reject, or request clarification.

Request:
```json
{
  "review_status": "approved",
  "reviewed_by": "endpoint_engineer",
  "edited_rule": null
}
```

## Rules

### GET `/rules/approved`
Returns approved normalized rules.

### GET `/rules/{rule_id}`
Returns one approved rule.

## Inventory

### POST `/inventory/upload`
Uploads mock inventory snapshot.

### GET `/inventory/snapshots`
Lists snapshots.

### GET `/inventory/{inventory_snapshot_id}/devices`
Lists devices.

### GET `/devices/{device_id}`
Returns device, components, readiness, latest compliance result.

## Compliance

### POST `/compliance/scan`
Runs deterministic compliance scan.

Request:
```json
{
  "inventory_snapshot_id": "INV-000001",
  "ruleset_version": "ruleset-2026-06-19-001"
}
```

Response:
```json
{
  "scan_id": "SCAN-000001",
  "status": "completed",
  "summary": {}
}
```

### GET `/compliance/scans/{scan_id}`
Returns scan metadata and summary.

### GET `/compliance/scans/{scan_id}/results`
Returns device-level results.

### GET `/compliance/scans/{scan_id}/violations`
Returns violations.

## Graph

### POST `/graph/sync/rules`
Syncs approved rules into Neo4j.

### POST `/graph/sync/inventory/{inventory_snapshot_id}`
Syncs devices and components into Neo4j.

### POST `/graph/sync/compliance/{scan_id}`
Syncs violations/remediations into Neo4j.

### GET `/graph/devices/{device_id}/explanation`
Returns graph export for React Flow.

## Explanation

### GET `/devices/{device_id}/explain?scan_id=SCAN-000001`
Returns grounded explanation using PostgreSQL + Neo4j + pgvector + optional LLM.

### GET `/reports/scan/{scan_id}`
Returns rollout readiness report.
