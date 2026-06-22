# RISKS — CompatIQ

## 1. PDF extraction fails

Mitigation:
- Use cached/preloaded chunks for demo.
- Support TXT fallback.
- Use Chandra OCR only for selected pages.

## 2. LLM returns invalid JSON

Mitigation:
- Pydantic validation.
- One repair prompt.
- Manual rule fixture fallback.

## 3. Extracted rules are wrong

Mitigation:
- Human review required.
- Confidence score is advisory only.
- Source excerpt shown beside every rule.

## 4. Normalization mismatch

Mitigation:
- Alias map.
- Version parser tests.
- Human review of low-confidence mappings.

## 5. Neo4j integration takes too long

Mitigation:
- Store official results in PostgreSQL first.
- Generate graph export JSON fallback.
- Sync graph only for demo subset if needed.

## 6. Frontend consumes too much time

Mitigation:
- Build simple dashboard first.
- Prioritize device detail and rule review pages.
- Use table/cards before complex visuals.

## 7. Too much architecture for hackathon

Mitigation:
- Build compliance engine with fixtures first.
- Treat document extraction, LLM extraction, pgvector, and graph as additive layers.

## 8. Judges think this is only a PDF chatbot

Mitigation:
- Emphasize deterministic compliance engine.
- Show approved rules and exact version comparison.
- Show graph-based root cause and rollout-readiness report.
