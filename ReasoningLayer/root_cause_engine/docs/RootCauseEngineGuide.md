# Root Cause Analysis Engine Guide

## Architecture

Layer 4 Phase 4 takes an EvidencePackage from the Evidence Aggregation Layer
and produces an RCAReport with findings, risk levels, and enriched recommendations.

```
EvidencePackage
    |
    v
RootCauseService
    |-- RootCauseAnalyzer
    |       |-- ViolationDetector  (signal matching on evidence text)
    |       \-- RiskAssessor       (confidence + scope modifiers)
    \-- RecommendationEngine       (ontology-grounded enrichment)
    |
    v
RCAReport {query_id, device, intent, overall_risk, findings[]}
```

## Finding Structure

Each RCAFinding contains:
- `finding_id` — deterministic FIND-<8hex>
- `root_cause_id` — from `root_cause_types.json` (12 types)
- `violation_id` — from `violation_types.json` (10 types)
- `risk_level` — Informational|Low|Medium|High|Critical
- `recommendations` — ordered REC-* identifiers
- `enriched_recommendations` — full name and description from ontology
- `evidence_ids` — traceability to EvidencePackage

## Risk Levels

| Level | Score | Response |
|---|---|---|
| Informational | 0 | Next assessment |
| Low | 25 | 30 days |
| Medium | 50 | 10 business days |
| High | 75 | 24 hours |
| Critical | 100 | Immediate |

## Operation

```powershell
python ReasoningLayer/root_cause_engine/root_cause_service.py \
    "Why is Laptop001 non-compliant?" --offline

python -m pytest ReasoningLayer/root_cause_engine/tests/ -v
python -m pytest tests/ ReasoningLayer/ -v
```

## Extension

Add a new root cause to `root_cause_types.json`, map a signal in
`ViolationDetector._PATTERNS`, and add test coverage.
