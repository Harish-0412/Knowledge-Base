# CompatIQ Guardrail Layer — Design Document

## Purpose

The CompatIQ Guardrail Layer wraps the AI assistant and enforces strict
boundaries on what questions it will answer and how it answers them.

CompatIQ Assistant is not a general chatbot. It is a **bounded enterprise
compatibility reasoning assistant**. Its job is to answer human questions
related to:

- Compatibility rules and rule candidates
- Source document evidence and chunks
- Rule review status (pending, approved, rejected)
- Vendor release notes and document metadata
- Remediation guidance found in documents
- Known issues and unsupported configurations
- General compatibility concepts

The assistant must not answer unrelated questions, hallucinate compatibility
facts, invent source evidence, or claim capabilities that are not connected.

---

## Pipeline Architecture

Every request goes through a **10-step deterministic pipeline**:

```
Request
  │
  ▼
① ScopeCheck            ──► blocked_out_of_scope / blocked_unsafe
  │
  ▼
② IntentClassifier      ──► 19 possible intents
  │
  ▼
③ CapabilityCheck       ──► capability_missing if required module offline
  │
  ▼
④ RetrievalRouter       ──► routes intent → retriever(s)
  │
  ▼
⑤ Retrievers            ──► Document / Chunk / Candidate / ReviewStatus / Export
  │                          + stub adapters for KB / KG / Inventory / Compliance
  ▼
⑥ EvidenceChecker       ──► sufficient / partial / missing / capability_missing / unsafe
  │
  ▼
⑦ PromptBuilder         ──► grounded system+user prompt (for LLM mode)
  │
  ▼
⑧ AnswerGenerator       ──► deterministic or LLM-grounded answer
  │
  ▼
⑨ OutputValidator       ──► hallucination / OOS / device-claim detection
  │
  ▼
⑩ AuditLogger           ──► JSONL record to storage/guardrail_audit.jsonl
  │
  ▼
Response
```

---

## Scope Guardrail

**File**: `app/guardrails/scope_guardrail.py`

Uses two keyword sets and a regex injection detector:

- **In-scope keywords**: 80+ terms covering compatibility, rules, firmware, BIOS,
  drivers, OS, TPM, Secure Boot, vendors, review status, etc.
- **Out-of-scope keywords**: sports, movies, recipes, politics, jokes, etc.
- **Injection patterns**: 10 regex patterns covering ignore-instructions,
  reveal-prompt, jailbreak, DAN-mode, bypass-guardrail patterns.

Logic (in priority order):
1. Injection detected → `blocked_unsafe`
2. In-scope keywords present → `allowed`
3. Out-of-scope keywords only → `blocked_out_of_scope`
4. Ambiguous → `allowed` with confidence 0.5 (lean permissive for concept questions)

---

## Intent Classifier

**File**: `app/guardrails/intent_classifier.py`

Deterministic ranked predicate system. 19 intents, checked in priority order.
First match wins. No LLM required.

| Intent | Example Question |
|---|---|
| `normalized_rule_lookup` | "What does COMP-001 say?" |
| `rule_candidate_lookup` | "What rules were extracted?" |
| `review_status_lookup` | "Which candidates are pending review?" |
| `chunk_evidence_lookup` | "Show evidence for TPM 7.2.4.1" |
| `source_trace` | "Where does this rule come from?" |
| `remediation_from_document` | "How do I fix BIOS version?" |
| `unsupported_config_lookup` | "What configs are unsupported?" |
| `document_summary` | "Summarize this document" |
| `document_metadata_lookup` | "When was this document uploaded?" |
| `general_compatibility_concept` | "What is a minimum version rule?" |
| `capability_question` | "What can you answer?" |
| `requires_kg` | "Show KG path for COMP-001" |
| `requires_kb` | "Semantic search for approved rules" |
| `requires_inventory` | "Which devices violate this rule?" |
| `requires_compliance_scan` | "Show compliance violations" |
| `out_of_scope` | "Who won the cricket match?" |
| `handoff_status` | "What is the handoff status?" |
| `known_issue_lookup` | "What known issues exist?" |
| `compatibility_explanation` | "Is this config compatible?" |

---

## Capability Matrix

**File**: `app/guardrails/capabilities.py`

Controls which backend subsystems are connected. Driven by environment variables
so future KB/KG/inventory adapters plug in without code changes.

| Capability | Default | Env Flag |
|---|---|---|
| `document_intelligence` | ✓ Active | Always on |
| `rule_candidates` | ✓ Active | Always on |
| `review_status` | ✓ Active | Always on |
| `approved_rules` | ✗ Stub | `GUARDRAILS_APPROVED_RULES_ENABLED=true` |
| `knowledge_base` | ✗ Stub | `GUARDRAILS_KB_ENABLED=true` |
| `knowledge_graph` | ✗ Stub | `GUARDRAILS_KG_ENABLED=true` |
| `inventory` | ✗ Stub | `GUARDRAILS_INVENTORY_ENABLED=true` |
| `compliance_scan` | ✗ Stub | `GUARDRAILS_COMPLIANCE_ENABLED=true` |
| `remediation_engine` | ✗ Stub | `GUARDRAILS_REMEDIATION_ENABLED=true` |
| `audit_log` | ✓ Active | Always on |

---

## Retrievers

**File**: `app/guardrails/retrievers.py`

### Current (connected)

| Retriever | Pulls From |
|---|---|
| `DocumentRetriever` | `DocumentRepository` → `documents` table |
| `DocumentChunkRetriever` | `ChunkRepository` → `document_chunks` table |
| `RuleCandidateRetriever` | `RuleCandidateRepository` → `rule_candidates` table |
| `NormalizedCandidateRetriever` | Same repo, filtered to `normalization_status=normalized` |
| `ReviewStatusRetriever` | Same repo, filtered by `review_status` |
| `ExportRetriever` | Returns path metadata for exported documents |

### Stub (future)

| Retriever | When Connected |
|---|---|
| `KnowledgeBaseRetriever` | Set `GUARDRAILS_KB_ENABLED=true` + implement adapter |
| `KnowledgeGraphRetriever` | Set `GUARDRAILS_KG_ENABLED=true` + implement Neo4j adapter |
| `InventoryRetriever` | Set `GUARDRAILS_INVENTORY_ENABLED=true` + implement adapter |
| `ComplianceRetriever` | Set `GUARDRAILS_COMPLIANCE_ENABLED=true` + implement adapter |

---

## Answer Modes

The `response_mode` field in the API response indicates how the answer was generated:

| Mode | Meaning |
|---|---|
| `answered_with_document_evidence` | Evidence found and answer grounded in it |
| `answered_general_concept` | General compatibility concept, no retrieval needed |
| `blocked_out_of_scope` | Question outside CompatIQ domain |
| `blocked_unsafe` | Prompt injection or unsafe instruction detected |
| `capability_missing` | In-scope but required module not connected |
| `insufficient_evidence` | In-scope, capable, but no matching data found |
| `needs_human_review` | Candidates found but all pending review |
| `error` | Internal pipeline error |

---

## LLM Answer Mode (Optional)

By default, answers are **deterministic** (no LLM required). This ensures
all tests pass without Ollama running.

To enable LLM-grounded answers:

```bash
GUARDRAILS_USE_LLM_ANSWER=true
```

When enabled, the `PromptBuilder` creates a grounded prompt with:
- Strict system instructions (10 rules preventing hallucination)
- Evidence block (evidence items formatted as context)
- Unavailable subsystem declarations
- Known limitations

The LLM is only asked to synthesize from evidence. If it fails, the pipeline
falls back to the deterministic answer.

---

## Audit Log

Every request is logged to `storage/guardrail_audit.jsonl`. Fields logged:

- `timestamp`
- `question` (truncated to 500 chars)
- `document_id`, `candidate_id`
- `scope_allowed`, `intent`, `required_capabilities`, `available_capabilities`
- `retrievers_used`, `evidence_count`, `evidence_status`
- `response_mode`, `blocked`, `block_reason`
- `output_validation_warnings`
- `final_answer_preview` (truncated to 200 chars)

**Sensitive fields NOT logged**: API keys, LLM prompts, system instructions,
internal system state.

Override the log path with `GUARDRAIL_AUDIT_LOG=path/to/file.jsonl`.

---

## Output Validator

**File**: `app/guardrails/output_validator.py`

Validates the generated answer for:

1. Device compliance claims without inventory capability
2. Compliance scan result claims without scan capability
3. Knowledge Graph traversal claims without KG capability
4. "Approved and active rule" claims without approved_rules capability
5. Page number references not backed by retrieved evidence
6. Rule ID references not backed by retrieved evidence
7. Out-of-scope content in the answer (joke, sports, etc.)
8. Internal system instruction disclosure

Validators raise warnings that are surfaced in `guardrail_trace`.
Only items 7 and 8 block the answer entirely.

---

## Adding a New Capability (Example: Knowledge Graph)

1. Set env flag: `GUARDRAILS_KG_ENABLED=true`
2. Implement `KnowledgeGraphRetriever.retrieve()` in `app/guardrails/retrievers.py`
3. No other code changes needed — the capability matrix, intent classifier,
   evidence checker, retrieval router, and audit logger all pick it up automatically.
