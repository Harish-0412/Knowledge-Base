# ROADMAP — CompatIQ

## Phase 0 — Alignment and Contract Freeze

**Goal:** Freeze schemas, interfaces, and team ownership.

Deliverables:
- Source-of-truth docs
- JSON schemas
- API contracts
- Team task split
- Demo story

## Phase 1 — Mock Data and Rule Fixtures

**Goal:** Make the project demo-safe before AI extraction is complete.

Deliverables:
- 200-device mock inventory
- 20–30 manually verified approved rules
- Expected compliance output samples

## Phase 2 — PostgreSQL Data Layer

Deliverables:
- PostgreSQL schema
- Tables for documents, chunks, rules, inventory, scans, violations
- pgvector extension enabled

## Phase 3 — Compliance Engine First

Deliverables:
- Version normalizer
- Component normalizer
- Rule evaluator
- Readiness checker
- Score generator
- Violation generator

## Phase 4 — Neo4j Graph Layer

Deliverables:
- Rule graph sync
- Device graph sync
- Violation graph sync
- Root-cause graph traversal queries

## Phase 5 — Document Extraction

Deliverables:
- Upload endpoint
- Document page profiler
- PyMuPDF extractor
- Docling extractor
- Chandra OCR integration
- Chunking and evidence storage

## Phase 6 — LLM Rule Extraction

Deliverables:
- Gemma/Ollama adapter
- Rule extraction prompt
- JSON validation
- Repair loop
- Rule candidate storage

## Phase 7 — Human Review Workbench

Deliverables:
- Rule candidate review API
- Approve/edit/reject workflow
- Impact preview
- Approved rules store

## Phase 8 — Dashboard and Reports

Deliverables:
- Compliance dashboard
- Device detail page
- Rule review page
- Graph view
- Markdown/JSON report export

## Phase 9 — Final Demo Polish

Deliverables:
- Demo script
- Pitch deck support material
- Test run video backup
- Preloaded sample data
- Failure fallback plan
