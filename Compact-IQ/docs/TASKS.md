# TASKS — Team Ownership

## Role 1 — AI Document and Rule Extraction Engineer

Owns:
- Document profiling
- Extraction router
- PyMuPDF / Docling / Chandra OCR integration
- Intelligent chunking
- LLM rule extraction prompt
- Rule candidate generation

Must produce:
- `document_chunks`
- `rule_candidates`
- extraction quality scores
- source evidence links

Must not decide:
- final compliance status
- final rule approval

## Role 2 — Compliance Engine and Normalization Engineer

Owns:
- Component normalization
- Version normalization
- Operator normalization
- Inventory normalization
- Rule evaluator
- Readiness checks
- Compliance scoring
- Violation generation

Must produce:
- normalized inventory
- compliance scan results
- violations
- readiness failures

This is the core logic role.

## Role 3 — Data and Backend Engineer

Owns:
- FastAPI app structure
- PostgreSQL schema and migrations
- pgvector setup
- API endpoints
- JSON schema validation
- Service integration
- Error handling

Must maintain:
- schema compatibility
- stable endpoint contracts
- data persistence

## Role 4 — Knowledge Graph Engineer

Owns:
- Neo4j schema
- Rule graph sync
- Device graph sync
- Violation graph sync
- Root-cause graph queries
- Graph export for UI

Must produce:
- graph node/edge contracts
- Cypher queries
- graph path outputs

## Role 5 — Frontend, Demo, and Documentation Engineer

Owns:
- Dashboard UI
- Rule review workbench
- Compliance results page
- Device detail page
- Graph view
- Demo flow
- README and pitch support

Must focus on:
- clarity
- explainability
- low demo risk

## Integration Rules

1. Every module must use the schemas in `SCHEMAS.md` and `/schemas`.
2. No teammate should invent fields without updating schemas.
3. Every generated rule must preserve `source_chunk_id`.
4. Every compliance result must include `scan_id` and `device_id`.
5. Neo4j graph is synced from PostgreSQL records, not manually invented.
6. If a schema change is required, update `SCHEMAS.md`, JSON schema files, API contracts, and examples together.
