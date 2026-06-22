# CompatIQ Guardrail Layer — API Reference

## Endpoint

```
POST /api/assistant/guarded-query
```

### Request Body

```json
{
  "question": "string (required)",
  "document_id": "string | null (optional — scope to a specific document)",
  "candidate_id": "string | null (optional — scope to a specific candidate)",
  "device_id": "string | null (optional — future: scope to a device)",
  "mode": "string (default: document_intelligence_only)",
  "include_guardrail_trace": true
}
```

### Response Body

```json
{
  "allowed": true,
  "intent": "review_status_lookup",
  "mode": "answered_with_document_evidence",
  "answer": "Found 3 rule candidate(s) matching your query...",
  "evidence_used": [
    {
      "source_type": "rule_candidate",
      "source_id": "42",
      "title": "COMP-001",
      "text": "TPM Firmware minimum version constraint...",
      "source_document_id": "DOC-abc123",
      "source_page": null,
      "source_excerpt": "TPM Firmware 7.2.4.1 or later is required.",
      "confidence": 0.92,
      "review_status": "pending_review",
      "metadata": {
        "rule_type": "min_version_constraint",
        "severity": "critical"
      }
    }
  ],
  "limitations": [
    "The matching rule candidates are still pending review..."
  ],
  "suggested_next_actions": [
    "Open the source document in the Documents page.",
    "Review the matching candidates in the Rule Review Queue."
  ],
  "guardrail_trace": {
    "scope_check": {
      "allowed": true,
      "confidence": 0.84,
      "reason": "In-scope keywords detected: candidate, review",
      "is_injection": false
    },
    "intent": {
      "classified_as": "review_status_lookup",
      "confidence": 0.92,
      "reason": "Review status / approval queue lookup",
      "required_capabilities": ["review_status"]
    },
    "evidence": {
      "status": "partial",
      "reason": "Evidence found but with limitations.",
      "retrievers_used": ["review_status"]
    },
    "capabilities": {
      "document_intelligence": true,
      "rule_candidates": true,
      "review_status": true,
      "approved_rules": false,
      "knowledge_base": false,
      "knowledge_graph": false,
      "inventory": false,
      "compliance_scan": false,
      "remediation_engine": false
    },
    "response_mode": "answered_with_document_evidence",
    "output_validation_warnings": []
  }
}
```

---

## Response Mode Reference

| `mode` | `allowed` | Description |
|---|---|---|
| `answered_with_document_evidence` | `true` | Evidence found, grounded answer |
| `answered_general_concept` | `true` | Concept explanation, no retrieval needed |
| `blocked_out_of_scope` | `false` | Question outside CompatIQ domain |
| `blocked_unsafe` | `false` | Prompt injection detected |
| `capability_missing` | `true` | In-scope but required module not connected |
| `insufficient_evidence` | `true` | In-scope + capable, but no data found |
| `needs_human_review` | `true` | Only pending candidates found |
| `error` | `false` | Internal pipeline error |

---

## Legacy Endpoint (Backward Compatible)

```
POST /api/assistant/query
```

**Request**: `{ "question": "string" }`

**Response**:
```json
{
  "response": "string",
  "mode": "answered_with_document_evidence",
  "intent": "review_status_lookup",
  "allowed": true
}
```

Routes through the same guardrail pipeline but returns a simplified
`{response, mode, intent, allowed}` shape for backward compatibility
with the existing frontend chat component.

> **Note**: The old `/api/assistant/query` stub in `frontend_compat.py`
> takes priority because it is registered first. The new guarded version
> at `assistant_guarded.py` is always available at `/api/assistant/guarded-query`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GUARDRAILS_USE_LLM_ANSWER` | `false` | Enable LLM-grounded answers |
| `GUARDRAILS_KB_ENABLED` | `false` | Connect Knowledge Base retriever |
| `GUARDRAILS_KG_ENABLED` | `false` | Connect Knowledge Graph retriever |
| `GUARDRAILS_INVENTORY_ENABLED` | `false` | Connect Inventory retriever |
| `GUARDRAILS_COMPLIANCE_ENABLED` | `false` | Connect Compliance Scan retriever |
| `GUARDRAILS_REMEDIATION_ENABLED` | `false` | Enable Remediation Engine |
| `GUARDRAILS_APPROVED_RULES_ENABLED` | `false` | Connect Approved Rules repository |
| `GUARDRAIL_AUDIT_LOG` | `storage/guardrail_audit.jsonl` | Audit log path |

---

## Example Requests

### Rule lookup
```bash
curl -s -X POST http://127.0.0.1:8000/api/assistant/guarded-query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does COMP-001 say?", "include_guardrail_trace": true}' | python -m json.tool
```

### Review status
```bash
curl -s -X POST http://127.0.0.1:8000/api/assistant/guarded-query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which candidates are pending review?"}'
```

### Blocked — out of scope
```bash
curl -s -X POST http://127.0.0.1:8000/api/assistant/guarded-query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who won the cricket match?"}'
```

### Capability missing
```bash
curl -s -X POST http://127.0.0.1:8000/api/assistant/guarded-query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which devices violate COMP-006?"}'
```

### General concept
```bash
curl -s -X POST http://127.0.0.1:8000/api/assistant/guarded-query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a minimum version rule?"}'
```
