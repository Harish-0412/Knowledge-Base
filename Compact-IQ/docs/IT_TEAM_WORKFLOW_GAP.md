# IT Team Workflow Gap

Current branch: `Dharani-dev`

This file describes the gap between the current merged application and the workflow an IT infrastructure or compliance team would expect.

## Expected IT Workflow

An IT user usually needs to answer:

1. Which document introduced this rule?
2. What exact source text supports it?
3. Which hardware, OS, firmware, feature, or license does it apply to?
4. Which devices are affected?
5. Is this a blocker, warning, or informational finding?
6. What is the remediation action?
7. Who approved the rule and when?
8. What changed since the last document or release?
9. Can the team export or audit the decision?

## Current Workflow Coverage

| Workflow need | Current status |
| --- | --- |
| Upload source document | Implemented |
| Extract chunks and candidates | Implemented |
| Normalize rule candidates | Implemented |
| Human review status | Temporary implementation |
| Source evidence trail | Partially visible |
| Approved rule repository | Not fully implemented |
| Inventory sync | Placeholder |
| Device impact analysis | Not implemented |
| Compliance scan | Placeholder |
| Remediation planning | Not implemented |
| Reviewer audit trail | Not implemented |
| Change/version tracking | Not implemented |

## Highest-Impact Gaps

1. Approval is not a governance workflow yet.

   The UI can mark a candidate as approved, but the backend does not create a canonical approved rule with reviewer identity, evidence, version, and downstream availability.

2. IT impact is missing.

   The app does not yet answer which devices are affected by a rule. Inventory and compliance pages are placeholders.

3. Evidence is not first-class in the React UI.

   Source excerpt exists, but chunk, page, raw output, normalized fields, and quality warnings are not presented as a full review packet.

4. Compliance status can be misleading.

   Compliance pages display operational structures while the backend returns placeholder results.

5. No operational handoff exists after review.

   There is no assignment, remediation task, exception workflow, waiver, or exportable review package.

## Brainstorming Topics Before Further Buildout

- What should count as an approved rule?
- What fields are mandatory before approval?
- Should approval require source page, source excerpt, confidence reason, and normalized JSON validation?
- What does the IT team need to see first: document evidence, affected devices, or remediation?
- Should the app distinguish document extraction review from compliance enforcement review?
- How should exceptions and waivers be represented?
- What inventory schema is the first supported target?
- What is the minimum useful compliance result: per device, per rule, or grouped by model/OS?
- Should the assistant be allowed to answer from candidates, only approved rules, or both with labels?
- What audit events must be immutable?

## Suggested Product Boundary

For the next implementation phase, keep the current app focused on:

1. Document Intelligence trust and review.
2. Canonical approved-rule creation.
3. Clear handoff from approved rules to future inventory/compliance workflows.

Avoid making Inventory, Compliance, Analysis, and Assistant look final until their backend services are real.

