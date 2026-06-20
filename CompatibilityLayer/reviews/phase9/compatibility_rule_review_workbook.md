# Compatibility Rule Review Workbook

## Dataset Summary
- Source candidates: 42
- Generated rules: 11
- Clarification items: 32
- Pending human decisions: 11

## Phase 8 Validation Summary
- Status: PASSED_WITH_WARNINGS
- Passed rules: 11
- Structural/schema errors: 0
- Warnings: 11 (authoritative evidence verification pending)

## Rule Review Table
| Rule ID | Source Candidates | Type | Predicate | Subject | Target | Conditions | Evidence | Phase 8 | Recommendation | Approval |
|---|---|---|---|---|---|---:|---|---|---|---|
| CRULE-FBAB6E52A6005CC3-001 | RCAND-000360 | min_version_constraint | REQUIRES | Enterprise OS | Driver Pack | 1 | review_required | PASS | needs_clarification | pending |
| CRULE-55ADFDEDAD3CD919-001 | RCAND-000362 | known_issue_fixed | FIXED_BY | Enterprise OS | EDR Agent | 2 | review_required | PASS | needs_clarification | pending |
| CRULE-AEADF7F483FE03B6-001 | RCAND-000363 | min_version_constraint | REQUIRES | BIOS | System Firmware | 1 | review_required | PASS | needs_clarification | pending |
| CRULE-38D745D2F59A2285-001 | RCAND-000364 | readiness_requirement | REQUIRES | System Firmware | Platform Driver Pack | 1 | review_required | PASS | needs_clarification | pending |
| CRULE-8C74D7E72507C9FD-001 | RCAND-000366 | min_version_constraint | REQUIRES | EDR Agent | Endpoint Agent | 1 | review_required | PASS | needs_clarification | pending |
| CRULE-14AFEDA269990CAD-001 | RCAND-000371 | min_version_constraint | REQUIRES | Enterprise OS | Driver Pack | 1 | review_required | PASS | needs_clarification | pending |
| CRULE-26AF9B5E643E194B-001 | RCAND-000372 | incompatible_combination | CONFLICTS_WITH | EDR Agent | Endpoint Agent | 2 | review_required | PASS | needs_clarification | pending |
| CRULE-279369EA931D9982-001 | RCAND-000373 | incompatible_combination | CONFLICTS_WITH | BIOS | System Firmware | 2 | review_required | PASS | needs_clarification | pending |
| CRULE-6C513DB9B0A7D3CB-001 | RCAND-000381 | readiness_requirement | REQUIRES | Enterprise OS | Driver Pack | 1 | review_required | PASS | needs_clarification | pending |
| CRULE-F51505E338E8B1D0-001 | RCAND-000397 | readiness_requirement | REQUIRES | BIOS | System Firmware | 1 | review_required | PASS | needs_clarification | pending |
| CRULE-A93082DE51586EFE-001 | RCAND-000399 | readiness_requirement | REQUIRES | Enterprise OS | Driver Pack | 1 | review_required | PASS | needs_clarification | pending |

## Rules Recommended for Approval
Count: 0. See the corresponding JSON review artifact for record-level details.

## Rules Recommended for Approval With Corrections
Count: 0. See the corresponding JSON review artifact for record-level details.

## Rules Recommended for Rejection
Count: 0. See the corresponding JSON review artifact for record-level details.

## Deferred Rules
Count: 0. See the corresponding JSON review artifact for record-level details.

## Rules Needing Clarification
Count: 11. See the corresponding JSON review artifact for record-level details.

## High-Risk Rules
Count: 11. See the corresponding JSON review artifact for record-level details.

## Evidence Gaps
Count: 11. See the corresponding JSON review artifact for record-level details.

## Entity-Resolution Gaps
Count: 3. See the corresponding JSON review artifact for record-level details.

## Version-Resolution Gaps
Count: 1. See the corresponding JSON review artifact for record-level details.

## Contradictions and Overlaps
Count: 17. See the corresponding JSON review artifact for record-level details.

## Special-Candidate Review
- RCAND-000361: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000365: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000367: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000368: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000369: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000374: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000376: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000377: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000382: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000385: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000398: previous warnings remain in clarification_review.json; no approval recommended.
- RCAND-000400: previous warnings remain in clarification_review.json; no approval recommended.

## Reviewer Instructions
1. Open `compatibility_rule_review_decisions.json`.
2. Review the source excerpt against the authoritative document and Phase 8 result.
3. Edit only `recommended_decision` if needed, `approval_status`, `approved_by`, `approval_date`, and `review_notes`.
4. Use `approval_status: approved` only after completing authoritative evidence and semantic checks.
5. Review every record in `clarification_review.json`; clarification records do not become approved rules automatically.

## Exact Human-Editable Fields
`recommended_decision`, `approval_status`, `approved_by`, `approval_date`, and `review_notes` in `compatibility_rule_review_decisions.json`.
