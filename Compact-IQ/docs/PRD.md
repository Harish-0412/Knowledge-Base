# PRD — CompatIQ

## 1. Product Summary

CompatIQ is an AI-assisted compatibility and configuration compliance engine for enterprise endpoint/server fleets. It ingests vendor compatibility documents such as PDFs, release notes, and matrices; extracts machine-readable rule candidates; lets IT engineers review and approve those rules; validates device inventory; identifies incompatible or rollout-unsafe systems; and explains root causes with remediation paths.

## 2. Problem

Enterprise endpoint and infrastructure teams manage thousands of devices with different BIOS, firmware, OS, drivers, agents, and management tools. Compatibility rules are often hidden inside static PDFs, release notes, tables, footnotes, and vendor advisories. Manual cross-checking is slow, error-prone, and does not scale.

## 3. Target Users

- Endpoint engineering teams
- Enterprise IT administrators
- Platform SREs
- Device management / patch management teams
- Infrastructure operations teams

## 4. Core User Stories

### Document-to-rule workflow
As an endpoint engineer, I want to upload a compatibility PDF/release note so that the system extracts candidate compatibility rules with source evidence.

### Human review workflow
As an endpoint engineer, I want to review extracted rules with the original source text beside them so that I can approve, edit, or reject them before they impact compliance.

### Fleet compliance workflow
As an IT administrator, I want to scan device inventory against approved rules so that I know which devices are compliant, critical, warning, unknown, or not rollout-ready.

### Root-cause workflow
As a platform SRE, I want to understand the root blocker for each device so that I can fix prerequisites in the correct order.

### Reporting workflow
As an IT lead, I want a rollout-readiness report so that I can decide which devices are safe for pilot/ring deployment.

## 5. MVP Scope

### Must-have
- Upload/load compatibility document
- Page-level extraction profiling
- Text/table/OCR extraction route
- Intelligent chunking
- Chunk evidence storage
- LLM rule candidate extraction
- Rule normalization and validation
- Human rule review
- Approved rule store
- 200-device mock inventory
- Inventory normalization
- Deterministic compliance scan
- Compatibility score
- Rollout readiness checks
- Violation detection
- Root-cause explanation
- Remediation steps
- PostgreSQL source of truth
- Neo4j relationship graph
- pgvector semantic evidence search
- Dashboard-ready API responses

### Should-have
- Rule impact preview before approval
- Rule confidence score and reason
- Similar chunk/rule retrieval
- Knowledge graph visualization
- Exportable JSON/Markdown report

### Stretch
- Conversational admin assistant
- Auto-generated remediation scripts
- Multi-document conflict resolution
- OCR quality scoring dashboard
- Sigma.js fleet-wide graph view
- Scheduling rollout rings automatically

## 6. Explicit Non-goals

- Do not push real updates to devices.
- Do not integrate with real Intune/SCCM/CMDB during MVP.
- Do not allow LLMs to make final compliance decisions.
- Do not skip human review before approved rules are used.
- Do not build a generic PDF chatbot as the core product.

## 7. Success Metrics

- Extract at least 20 rule candidates from sample documents.
- Human-review workflow supports approve/edit/reject.
- Scan 200 mock devices in a repeatable way.
- Show compliant, warning, critical, unknown, and not-ready states.
- Explain at least 3 distinct violation types.
- Demonstrate at least 1 compound AND-condition rule.
- Demonstrate at least 1 root-cause dependency chain.
- Demonstrate source evidence for each shown violation.
