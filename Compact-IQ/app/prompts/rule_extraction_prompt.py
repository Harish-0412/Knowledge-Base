def build_rule_extraction_prompt(
    *,
    document_id: str,
    chunk_id: int,
    source_excerpt: str,
    chunk_text: str,
    section_title: str | None = None,
    chunk_type: str | None = None,
    page_number: int | None = None,
    extraction_method: str | None = None,
    document_metadata_summary: str | None = None,
) -> str:
    return f"""
You are extracting raw compatibility/configuration rule candidates for human review.

Return JSON only. Do not include markdown fences, explanations outside JSON, or prose before/after JSON.

Extract only compatibility, supportability, firmware, BIOS, driver, OS, version, upgrade, downgrade, back-flashing, or configuration rules.
Do not invent rules. If the text does not contain a rule, return {{"rule_candidates": []}}.
If a rule is inferred rather than explicit, lower confidence_score and explain that in confidence_reason.
A chunk may contain ZERO, ONE, or MULTIPLE distinct rules. If multiple, return multiple separate items in rule_candidates; do not merge them into one.
Do NOT invent a rule or a version number. If no compatibility/version requirement is explicitly or implicitly stated, omit it entirely; never default to a placeholder value.

CRITICAL vendor-revision guardrail:
Phrases like "Updated ME to Rev Y", "Updated ACM to Rev Y", "Updated chipset/reference code/microcode to Rev Y", or "compliant with latest BIOS specification updates Rev (Y)" describe internal vendor revision numbers, NOT compatibility requirements, and NOT the BIOS product version. Only treat a version as a BIOS product version requirement if it is explicitly framed as a requirement/support condition on the BIOS itself, such as "requires BIOS >= Y", "not supported below BIOS Y", or "added support ... in version Y" where Y is the document's own release version from the document metadata context.

The LLM must produce only these content fields:
- candidate_kind
- rule_type
- condition_logic
- conditions
- requirements
- exceptions
- severity
- confidence_score
- confidence_reason
- remediation_hint

Do not produce candidate_id, source_document_id, source_chunk_id, source_page, source_excerpt, review_status, created_at, tags, condition_id, or requirement_id. The calling code assigns those fields.

Use this JSON shape:
{{
  "rule_candidates": [
    {{
      "candidate_kind": "support_matrix_fact | compliance_rule | unsupported_feature | known_limitation | operational_warning | informational_note | not_a_rule",
      "rule_type": "min_version_constraint | max_version_constraint | exact_version_constraint | incompatible_combination | feature_support_added | known_issue_fixed | deprecated_after | update_order_constraint | readiness_requirement | model_support_min_version | network_module_support_min_version | license_support_fact | software_image_fact | rommon_version_fact | unsupported_feature | configuration_requirement | upgrade_order_constraint | operational_warning | known_limitation | not_a_rule",
      "condition_logic": "AND | OR",
      "conditions": [
        {{"component_type": "cpu", "component_name": null, "component_family": "Intel Xeon E5-2400 V2", "vendor": "Intel", "operator": "installed", "value_raw": "Intel Xeon E5-2400 V2 family", "version_raw": null, "version_scheme": null}}
      ],
      "requirements": [
        {{"component_type": "bios", "component_name": "System BIOS", "component_family": null, "vendor": null, "operator": ">=", "value_raw": null, "version_raw": "2.0.21", "version_scheme": "semantic", "requirement_kind": "min_version"}}
      ],
      "exceptions": [],
      "severity": "info | warning | critical | blocker",
      "confidence_score": 0.0,
      "confidence_reason": "why this confidence was assigned",
      "remediation_hint": "short human-readable remediation, or null"
    }}
  ]
}}

Cisco support matrix guidance:
- A table row like "Switch Model: C9200-24T-A | Introductory Release: Cisco IOS XE Gibraltar 16.10.1" is a support matrix fact, not automatically an enforceable compliance rule.
- Extract it as candidate_kind "support_matrix_fact", rule_type "model_support_min_version", condition component_type "device_model" with value_raw "C9200-24T-A", and requirement component_type "network_os", component_name "Cisco IOS XE", component_family "Gibraltar", operator ">=", version_raw "16.10.1", version_scheme "cisco_ios_xe", requirement_kind "min_version".
- Network module introductory release rows use rule_type "network_module_support_min_version" and condition component_type "network_module".
- Feature rows that say "not supported" use candidate_kind "unsupported_feature", rule_type "unsupported_feature", requirement operator "not_supported", and requirement_kind "not_supported".

EXAMPLE 1 - explicit, conditional rule:
Text: "Back-flashing to BIOS versions earlier than 2.0.21 is not allowed if Intel Xeon E5-2400 V2 family processors are installed."
Correct extraction: a min_version_constraint rule with condition {{component_type: cpu, component_family: "Intel Xeon E5-2400 V2", operator: installed}}, requirement {{component_type: bios, operator: >=, requirement_kind: min_version, version_raw: "2.0.21"}}, severity critical, confidence_score about 0.95 because this is explicit.

EXAMPLE 2 - TRAP, do not extract a rule from this:
Text: "Updated Intel chipset configuration compliant with latest BIOS specification updates Rev (2.0.8)."
This does NOT state a BIOS version requirement. "Rev (2.0.8)" is Intel's internal spec document revision. Correct extraction: return NO rule_candidate for this text.

EXAMPLE 3 - implicit rule from a feature-support announcement:
Text: "Added support for Intel Xeon E5-2400 V2 family of processors." appearing under a release versioned 2.0.21 in the document.
Correct extraction: feature_support_added rule, condition {{cpu, "Intel Xeon E5-2400 V2", installed}}, requirement {{bios, >=, min_version, "2.0.21"}}, severity warning, confidence_score about 0.65 because this is inferred from an announcement, not an explicit requirement statement.

Document ID: {document_id}
Chunk ID: {chunk_id}
Page number: {page_number}
Section title: {section_title or ""}
Chunk type: {chunk_type or ""}
Extraction method: {extraction_method or ""}
Source excerpt: {source_excerpt}
Document metadata context: {document_metadata_summary or ""}

Chunk text:
{chunk_text}
""".strip()
