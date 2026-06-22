# PROMPTS — LLM Usage

## Important Rule

LLM output is never final truth. It must pass validation, normalization, and human review.

## 1. Rule Extraction Prompt

```text
You are extracting compatibility and configuration compliance rules from enterprise release notes or compatibility documents.

Return only valid JSON matching the provided schema. Do not include prose outside JSON.

Extract only rule-bearing statements:
- minimum required versions
- unsupported/incompatible combinations
- known issues fixed by a version
- feature support introduced in a version
- update order requirements
- readiness requirements

Do not extract cosmetic changes, internal binary updates, generic improvements, copyright changes, or unrelated notes.

For each rule candidate include:
- rule_type
- condition_logic
- conditions
- requirements
- severity
- confidence_score
- confidence_reason
- source_excerpt
- remediation_hint

If a rule is inferred rather than explicitly stated, lower the confidence and explain why.
```

## 2. JSON Repair Prompt

```text
The following LLM output failed JSON schema validation.
Repair it without changing the intended meaning.
Return only valid JSON.
Validation errors:
{{errors}}
Original output:
{{raw_output}}
```

## 3. Ambiguous Normalization Prompt

```text
Map the following component/value to the closest normalized enterprise inventory component.
Return JSON with normalized_component_type, normalized_name, normalized_family, confidence_score, and needs_human_review.

Raw component:
{{raw_component}}
Known catalog:
{{component_catalog}}
```

## 4. Grounded Explanation Prompt

```text
You are generating an IT administrator explanation.
Use only the provided facts. Do not invent additional causes or versions.

Device facts:
{{device}}
Violation facts:
{{violation}}
Rule facts:
{{rule}}
Source evidence:
{{source_evidence}}
Remediation steps:
{{remediation}}

Explain:
1. Why the device is blocked or risky.
2. Which rule caused it.
3. What source evidence supports it.
4. What remediation should happen first.
Keep the answer concise and operational.
```
