# ARCHITECTURE — CompatIQ

## 1. Architecture Principle

CompatIQ uses a hybrid architecture:

- **PostgreSQL** is the authoritative source of truth.
- **pgvector** is semantic memory for evidence retrieval.
- **Neo4j** is the relationship graph for rules, devices, violations, and remediation chains.
- **Python deterministic code** evaluates compliance.
- **LLM** extracts, repairs, and explains, but does not decide compliance.

## 2. Final End-to-End Pipeline

```text
Compatibility Documents
PDF / TXT / DOCX / CSV / Release Notes
        ↓
Document Profiling
        ↓
Extraction Router
PyMuPDF / Docling / Chandra OCR
        ↓
Intelligent Chunking
        ↓
PostgreSQL Chunk Store
        ↓
pgvector Semantic Memory
        ↓
LLM Rule Candidate Extraction
Gemma 4 via Ollama Cloud
        ↓
Rule Normalization
Deterministic code + optional LLM repair
        ↓
Rule Validation
Pydantic + schema checks
        ↓
Human Review Workbench
Approve / Edit / Reject / Needs clarification
        ↓
Approved Rule Store
PostgreSQL
        ↓
Neo4j Rule Knowledge Graph
        ↓
Inventory Ingestion
PostgreSQL
        ↓
Inventory Normalization
        ↓
Device Graph Sync
Neo4j
        ↓
Compliance Engine
Deterministic Python evaluator
        ↓
Violation + Score Generation
PostgreSQL
        ↓
Neo4j Compliance Graph
        ↓
Root Cause + Remediation Engine
Neo4j traversal + templates
        ↓
Template + AI Explanation Layer
        ↓
Dashboard + Graph UI + Reports
```

## 3. Storage Responsibilities

### PostgreSQL
Stores authoritative records:

- Documents
- Pages
- Chunks
- Rule candidates
- Approved rules
- Inventory snapshots
- Devices
- Device components
- Scan runs
- Compliance results
- Violations
- Readiness failures
- Review history
- Reports

### pgvector
Stores embeddings for semantic retrieval:

- Document chunks
- Approved rules
- Rule candidates, optional
- Violation patterns, optional

### Neo4j
Stores graph relationships:

- Rule → condition set
- Rule → requirement
- Rule → source chunk
- Device → component instance
- Device → violates rule
- Violation → observed component
- Violation → expected requirement
- Violation → remediation step

## 4. Retrieval Modes

### Direct retrieval
Used for dashboards, tables, counts, and exact data.

```text
UI → FastAPI → PostgreSQL / Neo4j → UI
```

### GraphRAG retrieval
Used for natural-language explanations.

```text
User question
    ↓
Intent detection
    ↓
PostgreSQL exact facts
    ↓
Neo4j graph path
    ↓
pgvector source evidence
    ↓
LLM grounded response
```

## 5. Compliance Decision Boundary

The compliance decision is generated only by deterministic code:

```text
approved normalized rules + normalized inventory → compliance engine → result
```

The LLM is never allowed to directly output final compliance status.
