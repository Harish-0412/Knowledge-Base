# CompatIQ Source of Truth

**Tagline:** Turn static compatibility documents into live compliance intelligence.

This repository pack is the coordination reference for every teammate building the hackathon project: **Dynamic Compatibility & Configuration Compliance Engine**.

The system converts static compatibility documents into human-reviewed, machine-readable rules, validates device inventory, detects incompatibilities and rollout-readiness issues, explains root causes, and recommends safe remediation paths.

## Golden Rule

**AI extracts and explains. Humans approve. Deterministic code decides compliance.**

No teammate should build logic that lets an LLM directly decide whether a device is compliant. LLM output must pass through validation, normalization, and human review before being used by the compliance engine.

## Document Index

| File | Purpose |
|---|---|
| `PRD.md` | Product requirements and user value |
| `ARCHITECTURE.md` | Final end-to-end system pipeline |
| `TECH_STACK.md` | Fixed stack choices and why |
| `DECISIONS.md` | Architecture decisions and rejected alternatives |
| `ROADMAP.md` | Phase-wise build plan |
| `TASKS.md` | Team role split and task ownership |
| `PROGRESS.md` | Current status tracker |
| `SCHEMAS.md` | Canonical JSON schemas and contracts |
| `API_CONTRACTS.md` | Backend API endpoint contracts |
| `DATABASE_SCHEMA.md` | PostgreSQL table plan |
| `GRAPH_MODEL.md` | Neo4j nodes, relationships, and Cypher examples |
| `PIPELINE.md` | Low-level data flow across modules |
| `NORMALIZATION.md` | Component/version/operator normalization rules |
| `MOCK_DATA_GUIDE.md` | How to create realistic 200-device inventory data |
| `PROMPTS.md` | LLM prompts for extraction, repair, and explanation |
| `DEMO_PLAN.md` | Final demo storyline |
| `TESTING.md` | Unit/integration/demo test plan |
| `RISKS.md` | Risks and mitigation strategies |

## Fixed Core Data Contracts

All teams must use the schema files in `/schemas`:

- `document.schema.json`
- `document_chunk.schema.json`
- `rule_candidate.schema.json`
- `approved_rule.schema.json`
- `inventory_snapshot.schema.json`
- `device.schema.json`
- `device_component.schema.json`
- `compliance_scan.schema.json`
- `compliance_result.schema.json`
- `violation.schema.json`
- `graph_export.schema.json`

Examples are in `/examples`.
