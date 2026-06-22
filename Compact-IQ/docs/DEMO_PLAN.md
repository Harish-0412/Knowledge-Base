# DEMO_PLAN — CompatIQ

## Demo Duration

Target: 4–6 minutes.

## Demo Story

1. Show a vendor release note / compatibility PDF.
2. Upload the document.
3. System profiles pages and selects extraction route.
4. System extracts chunks and stores evidence.
5. System generates rule candidates.
6. Open rule review workbench.
7. Approve/edit one rule.
8. Load 200-device mock inventory.
9. Run compliance scan.
10. Dashboard shows counts.
11. Open a critical device.
12. Show violated rule, observed vs expected version.
13. Show source evidence.
14. Show Neo4j graph path.
15. Show root cause and remediation.
16. Export rollout readiness report.

## Must-Demo Scenarios

### Scenario A — Direct version violation
Device has BIOS 2.0.21 but requires BIOS >= 2.4.2.

### Scenario B — Compound condition violation
Device matches OS + HBA + CPU condition and fails BIOS requirement.

### Scenario C — Readiness failure
Device is compatible but not ready because of pending reboot or agent unhealthy.

### Scenario D — Unknown/missing data
Device cannot be safely classified because firmware version is missing.

## Backup Plan

If live extraction fails:
- Use preloaded chunks.
- Use preloaded rule candidates.
- Explain that extraction is supported but demo uses cached output for reliability.

If Neo4j fails:
- Show graph export JSON or React Flow mock from precomputed graph file.

If LLM fails:
- Use manually verified rules and template explanations.
