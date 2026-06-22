# TECH_STACK — CompatIQ

## 1. Backend

| Layer | Stack | Reason |
|---|---|---|
| API server | FastAPI | Fast Python APIs, type hints, easy Pydantic integration |
| Data validation | Pydantic | Strong schema validation for rule/inventory contracts |
| Async runtime | Uvicorn | Standard FastAPI dev server |
| HTTP client | httpx | Async calls to LLM/Ollama/external services |

## 2. Document Extraction

| Need | Stack | Use |
|---|---|---|
| Text PDFs | PyMuPDF | Fast extraction from clean selectable PDFs |
| Structured documents/tables | Docling | Layout-aware table/document conversion |
| Scanned/image PDFs | Chandra OCR | OCR for scanned pages and image-heavy documents |
| CSV/Excel | pandas/openpyxl | Structured compatibility matrices and inventories |

## 3. AI Layer

| Layer | Stack | Notes |
|---|---|---|
| Primary LLM | Gemma 4 via Ollama Cloud API | Used for rule candidate extraction and explanation |
| Validation | Pydantic | All model output must validate |
| Repair | LLM repair prompt + deterministic fixer | Used only for invalid JSON or ambiguous fields |

## 4. Data Layer

| Storage | Stack | Role |
|---|---|---|
| Source of truth | PostgreSQL | All official data records |
| Semantic memory | pgvector | Embeddings for chunks/rules/evidence retrieval |
| Relationship graph | Neo4j | Rule/device/violation/remediation graph |
| Optional algorithm layer | NetworkX | Small subgraph analysis only, not full storage |

## 5. Frontend

| Need | Stack | Reason |
|---|---|---|
| UI | React + Vite + TypeScript | Fast frontend build |
| Styling | Tailwind CSS | Rapid consistent design system |
| Graph detail view | React Flow | Best for explainable device/rule/remediation graph |
| Fleet-wide graph stretch | Sigma.js | Better for very large graph visualization |
| Charts | Recharts | Dashboard summaries |

## 6. Testing

| Need | Stack |
|---|---|
| Unit tests | pytest |
| API tests | pytest + httpx |
| Frontend tests | Vitest, optional |
| Contract tests | JSON schema validation |

## 7. Environment

Recommended local services:

```text
backend: FastAPI
postgres: PostgreSQL + pgvector
neo4j: Neo4j Community/Enterprise container
frontend: React Vite
```
