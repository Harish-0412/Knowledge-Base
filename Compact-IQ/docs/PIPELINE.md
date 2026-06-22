# PIPELINE — Low-Level Data Flow

## 1. Document to Chunks

```text
upload document
  → profile pages
  → choose extraction method per page
  → extract text/table/OCR output
  → intelligent chunking
  → store chunks in PostgreSQL
  → generate chunk embeddings in pgvector
```

## 2. Chunks to Rule Candidates

```text
select chunk group
  → send to Gemma/Ollama extraction prompt
  → receive JSON-like output
  → validate raw JSON
  → normalize components/operators/versions
  → Pydantic validation
  → store rule candidate
```

## 3. Rule Candidates to Approved Rules

```text
human review workbench
  → show source evidence + interpreted rule
  → reviewer approves/edits/rejects
  → normalize again after edits
  → save approved rule in PostgreSQL
  → generate rule embedding
  → sync rule graph to Neo4j
```

## 4. Inventory to Normalized Device State

```text
upload/generate inventory snapshot
  → normalize device fields
  → normalize components and versions
  → store devices and components in PostgreSQL
  → sync device graph to Neo4j
```

## 5. Compliance Scan

```text
load approved rules
  → load normalized inventory
  → for each device:
        match rule conditions
        evaluate requirements
        evaluate rollout readiness
        compute score
        create violations
  → store scan/results/violations in PostgreSQL
  → sync compliance graph to Neo4j
```

## 6. Explanation

```text
user opens device
  → retrieve compliance result from PostgreSQL
  → retrieve graph path from Neo4j
  → retrieve source evidence from pgvector/PostgreSQL
  → generate template explanation
  → optional LLM polish
```
