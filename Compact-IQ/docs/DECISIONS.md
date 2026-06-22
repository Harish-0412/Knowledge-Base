# DECISIONS — CompatIQ

This file records architecture decisions. Do not change these without team agreement.

## ADR-001: PostgreSQL is the source of truth

**Decision:** Store official documents, chunks, rules, inventory, scan results, violations, review history, and reports in PostgreSQL.

**Reason:** PostgreSQL is reliable for transactional, structured, indexed records. Neo4j and pgvector are projections/indexes over this data, not replacements for it.

## ADR-002: Use pgvector for semantic retrieval

**Decision:** Store embeddings for chunks and approved rules using pgvector inside PostgreSQL.

**Reason:** Chunks already live in PostgreSQL. pgvector avoids introducing a separate vector DB for MVP.

## ADR-003: Use Neo4j for relationship graph

**Decision:** Store verified rule, device, violation, and remediation relationships in Neo4j.

**Reason:** Root-cause explanation, dependency chains, and source-evidence paths are graph-shaped.

## ADR-004: Compliance decisions are deterministic

**Decision:** The compliance engine uses Python logic over approved normalized rules and normalized inventory.

**Reason:** Version comparison and compliance decisions must be exact and auditable.

## ADR-005: LLM is not the compliance judge

**Decision:** LLMs are used for extraction, invalid JSON repair, ambiguity suggestions, summaries, and explanations only.

**Reason:** LLMs can hallucinate or miscompare versions.

## ADR-006: No auto-approval of rules in MVP

**Decision:** Rule candidates must be reviewed by humans before becoming approved rules.

**Reason:** Some release-note lines imply rules but are not explicit requirements.

## ADR-007: Build graph after approval

**Decision:** Neo4j rule graph is built from approved normalized rules, not raw chunks.

**Reason:** Raw text and raw LLM output are not reliable graph facts.

## ADR-008: Support rollout readiness separately from compatibility

**Decision:** Compliance scan produces both compatibility status and readiness status.

**Reason:** Devices can satisfy compatibility rules but still be unsafe to update due to offline state, pending reboot, low battery, low disk, unhealthy agent, etc.

## ADR-009: React Flow first, Sigma.js stretch

**Decision:** Use React Flow for device/rule/remediation graph views.

**Reason:** React Flow is better for detailed explainability graphs. Sigma.js is reserved for large fleet-wide graph visualization.

## ADR-010: 200 mock devices for demo

**Decision:** Mock inventory should contain 200 realistic devices.

**Reason:** This shows scalability better than tiny toy data while remaining easy for a hackathon demo.
