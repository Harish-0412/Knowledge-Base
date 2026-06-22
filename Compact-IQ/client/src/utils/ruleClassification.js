/**
 * ruleClassification.js
 *
 * Pure utility functions for tiering rule candidates and generating structured
 * decision prompts for the Document Intelligence rule review interface.
 *
 * No React, no side effects. Fully unit-testable.
 *
 * FIELD MAPPING NOTE:
 *   The spec references enforcement_type, human_review_needed, quality_warnings
 *   but these don't exist in the real API response. We derive them from:
 *     - confidence_score          (direct DB column)
 *     - severity                  (direct DB column → maps to enforcement_type)
 *     - tags                      (in normalized_rule_json → "unverified_value")
 *     - confidence_reason         (contains "[AUTO-FLAGGED:" when grounding fails)
 *     - normalization_status      ("needs_human_review")
 *     - conditions_json / requirement_json → component_type === "unknown"
 */

// ── Enforcement type derivation ────────────────────────────────────────────

/**
 * Maps severity string to a logical enforcement type.
 * blocker → hard_block | critical → mandatory | warning → advisory | else → info
 */
export function deriveEnforcementType(candidate) {
  const sev = (candidate.severity || "").toLowerCase();
  if (sev === "blocker" || sev === "critical") return "hard_block";
  if (sev === "warning") return "advisory";
  if (sev === "info" || sev === "silent") return "silent_failure";
  return "advisory"; // safe default
}

// ── Quality warning derivation ─────────────────────────────────────────────

/**
 * Derives an array of quality warning strings from the real candidate fields.
 * Returns [] if the candidate is clean.
 */
export function deriveQualityWarnings(candidate) {
  const warnings = [];

  // Grounding failure flag — set by rule_extraction_service when value not verbatim in source
  const cr = candidate.confidence_reason || "";
  if (cr.includes("[AUTO-FLAGGED:")) {
    warnings.push("Grounding failure: extracted value not found verbatim in source text.");
  }

  // Tags-based flag (normalized_rule_json.tags or top-level tags)
  const nrj = candidate.normalized_rule_json || {};
  const tags = Array.isArray(nrj.tags)
    ? nrj.tags
    : Array.isArray(candidate.tags)
    ? candidate.tags
    : [];
  if (tags.includes("unverified_value")) {
    if (!warnings.some(w => w.startsWith("Grounding"))) {
      warnings.push("Grounding failure: extracted value not found verbatim in source text.");
    }
  }

  // Normalization service flagged this for human review
  if (candidate.normalization_status === "needs_human_review") {
    warnings.push("Flagged by normalization engine: requires human verification.");
  }

  // Unknown component types make downstream matching impossible
  const conditions = nrj.conditions || candidate.conditions_json || [];
  const requirements = nrj.requirements || candidate.requirement_json || [];
  const allParts = [
    ...(Array.isArray(conditions) ? conditions : [conditions]),
    ...(Array.isArray(requirements) ? requirements : [requirements]),
  ].filter(Boolean);
  if (allParts.some(p => p.component_type === "unknown")) {
    warnings.push("Unknown component type: inventory field cannot be matched.");
  }

  return warnings;
}

// ── Tier classification ────────────────────────────────────────────────────

/**
 * classifyRuleCandidate(candidate) → "auto" | "batch" | "individual"
 *
 * Tier logic (in priority order):
 *   INDIVIDUAL — any of: confidence < 0.83, quality warnings present, enforcement = silent_failure
 *   AUTO       — all of: status === pending_review, confidence ≥ 0.93, no warnings, hard enforcement
 *   BATCH      — everything else
 *
 * If the candidate already has a non-pending status it should NOT be auto-approved,
 * but it still gets classified so the UI can show it in the correct section.
 */
export function classifyRuleCandidate(candidate) {
  const confidence = candidate.confidence_score ?? 0;
  const warnings = deriveQualityWarnings(candidate);
  const enforcementType = deriveEnforcementType(candidate);

  // INDIVIDUAL tier conditions (any one is enough)
  const isIndividual =
    confidence < 0.83 ||
    warnings.length > 0 ||
    enforcementType === "silent_failure";

  if (isIndividual) return "individual";

  // AUTO tier conditions (ALL must be true, AND must be pending)
  const isAuto =
    candidate.review_status === "pending_review" &&
    confidence >= 0.93 &&
    warnings.length === 0 &&
    (enforcementType === "hard_block" || enforcementType === "mandatory");

  if (isAuto) return "auto";

  // BATCH — everything in between
  return "batch";
}

// ── Structured decision prompt generation ─────────────────────────────────

/**
 * Returns a structured prompt object for individual-tier candidates.
 * {
 *   question: string,
 *   options: [{ label, value, metadata? }],
 *   sourceHighlight: boolean,
 *   defaultTab: "evidence" | "summary" | "fields",
 * }
 */
export function getDecisionPrompt(candidate) {
  const warnings = deriveQualityWarnings(candidate);
  const confidence = candidate.confidence_score ?? 0;
  const nrj = candidate.normalized_rule_json || {};

  // Grounding failure (highest priority — most actionable)
  if (warnings.some(w => w.startsWith("Grounding failure"))) {
    return {
      flagType: "grounding_failure",
      question:
        "The AI extracted a value that wasn't found verbatim in the source text. Is this extraction accurate?",
      options: [
        { label: "Yes, the extraction is correct — approve", value: "approved" },
        { label: "No, the AI hallucinated — reject", value: "rejected" },
        { label: "I need to check the original document — needs clarification", value: "needs_clarification" },
      ],
      sourceHighlight: true,
      defaultTab: "evidence",
    };
  }

  // Normalization flagged it (human_review_needed equivalent)
  if (warnings.some(w => w.startsWith("Flagged by normalization"))) {
    const humanReason =
      candidate.human_review_reason ||
      nrj.human_review_reason ||
      "This rule was flagged by the normalization engine for human verification.";
    return {
      flagType: "normalization_flag",
      question: humanReason,
      options: [
        { label: "Apply as a hard failure (FAIL) — approve with enforcement override", value: "approved", meta: { enforcement_override: "hard_block" } },
        { label: "Apply as a warning only (WARN) — approve with advisory enforcement", value: "approved", meta: { enforcement_override: "advisory" } },
        { label: "Skip — not applicable to our environment", value: "rejected" },
        { label: "I need more information — needs clarification", value: "needs_clarification" },
      ],
      sourceHighlight: false,
      defaultTab: "summary",
    };
  }

  // Unknown component type
  if (warnings.some(w => w.startsWith("Unknown component type"))) {
    return {
      flagType: "unknown_component",
      question:
        "This rule references a component type that couldn't be classified. Can you identify what type of component this is?",
      options: [
        { label: "Yes, the classification is close enough — approve", value: "approved" },
        { label: "No, the component type is wrong — reject", value: "rejected" },
        { label: "I'm unsure — needs clarification", value: "needs_clarification" },
      ],
      sourceHighlight: false,
      defaultTab: "fields",
    };
  }

  // Low confidence (< 0.83)
  if (confidence < 0.83) {
    return {
      flagType: "low_confidence",
      question:
        "The AI has low confidence in this extraction. Does this rule accurately reflect the source document?",
      options: [
        { label: `Yes, approve as extracted (${Math.round(confidence * 100)}% confidence)`, value: "approved" },
        { label: "No, reject — incorrect extraction", value: "rejected" },
        { label: "Partially — needs clarification", value: "needs_clarification" },
      ],
      sourceHighlight: true,
      defaultTab: "evidence",
    };
  }

  // Fallback (should not normally reach here for individual tier)
  return {
    flagType: "generic",
    question: "Review this rule candidate carefully before making a decision.",
    options: [
      { label: "Approve", value: "approved" },
      { label: "Reject", value: "rejected" },
      { label: "Needs clarification", value: "needs_clarification" },
    ],
    sourceHighlight: false,
    defaultTab: "summary",
  };
}

// ── Rejection reasons ─────────────────────────────────────────────────────

/**
 * The canonical list of rejection reason options for the inline selector.
 * The last entry ("other") triggers a free-text input.
 */
export function getRejectionReasons() {
  return [
    { value: "ai_hallucination", label: "AI hallucination — extracted value does not exist in source" },
    { value: "incorrect_enforcement_type", label: "Incorrect enforcement type" },
    { value: "duplicate_rule", label: "Duplicate of another rule in this document" },
    { value: "not_applicable", label: "Not applicable to our environment" },
    { value: "ambiguous_source", label: "Ambiguous source — cannot determine intent" },
    { value: "other", label: "Other (add a note)" },
  ];
}
