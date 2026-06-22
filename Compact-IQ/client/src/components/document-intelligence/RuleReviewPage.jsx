/**
 * RuleReviewPage.jsx — Tiered Human Approval Interface (Redesigned)
 *
 * Clean light-theme version. Three tier lanes displayed as clearly distinct
 * visual panels. Auto-approved rules are always visible.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { candidateApi } from "../../lib/api";
import {
  classifyRuleCandidate,
  deriveQualityWarnings,
  getDecisionPrompt,
  getRejectionReasons,
} from "../../utils/ruleClassification";

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtConf(v) { return v == null ? "—" : `${Math.round(v * 100)}%`; }
function confClass(v) { if (v == null) return "neutral"; if (v >= 0.85) return "high"; if (v >= 0.65) return "mid"; return "low"; }

function statusLabel(s) {
  return { approved: "Approved", rejected: "Rejected", needs_clarification: "Needs Clarification", pending_review: "Pending Review", staged: "Staged" }[s] || (s || "Unknown");
}
function statusClass(s) {
  return { approved: "s-approved", rejected: "s-rejected", needs_clarification: "s-clarify", pending_review: "s-pending", staged: "s-staged" }[s] || "s-pending";
}
function sevClass(s) {
  const v = String(s || "").toLowerCase();
  if (v === "blocker" || v === "critical") return "sev-high";
  if (v === "warning") return "sev-warn";
  return "sev-info";
}

function ruleHeadline(c) {
  const n = c.normalized_rule_json || {};
  const raw = n.candidate_kind || n.rule_type || c.rule_type || "Compatibility Rule";
  return raw.replace(/_/g, " ").replace(/\b\w/g, ch => ch.toUpperCase());
}
function humanSummary(c) {
  const n = c.normalized_rule_json || {};
  const conds = n.conditions || [];
  const reqs = n.requirements || [];
  const c0 = conds[0] || {};
  const r0 = reqs[0] || {};
  if (c0.component_name && r0.component_name && r0.version_raw) {
    const op = r0.operator === ">=" ? "≥" : r0.operator === "==" ? "=" : (r0.operator || "≥");
    return `When ${c0.component_name} is present, ${r0.component_name} must be ${op} ${r0.version_raw}.`;
  }
  return c.source_excerpt ? c.source_excerpt.slice(0, 140).trim() + (c.source_excerpt.length > 140 ? "…" : "") : "No summary available.";
}
function readablePart(item) {
  if (!item) return "—";
  const name = item.component_name || item.component_type || item.value_raw || "Component";
  const op = item.operator || "is";
  const val = item.version_raw || item.value_raw || item.version_normalized || "";
  return `${name} ${op} ${val}`.trim();
}

function buildSecurityQuery(candidate) {
  const normalized = candidate.normalized_rule_json || {};
  const parts = [...(normalized.conditions || []), ...(normalized.requirements || [])];
  const terms = parts.flatMap(item => [item.component_name, item.product_name, item.vendor, item.version_raw])
    .filter(Boolean)
    .map(value => String(value).trim())
    .filter((value, index, all) => value.length > 1 && all.indexOf(value) === index);
  return terms.slice(0, 5).join(" ") || candidate.source_excerpt?.slice(0, 180) || ruleHeadline(candidate);
}

function SecurityImpactPanel({ candidate }) {
  const query = useMemo(() => buildSecurityQuery(candidate), [candidate]);
  const [state, setState] = useState({ loading: true, data: null, error: "" });
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ loading: true, data: null, error: "" });
    candidateApi.securityImpact({ query, results_per_page: 8 })
      .then(data => active && setState({ loading: false, data, error: "" }))
      .catch(error => active && setState({ loading: false, data: null, error: error.message || "Security lookup failed." }));
    return () => { active = false; };
  }, [candidate.candidate_id, query, refreshKey]);

  if (state.loading) {
    return <div className="rr2-security-state"><span className="rr2-security-spinner" />Checking the NVD for related vulnerabilities...</div>;
  }

  if (state.error) {
    return (
      <div className="rr2-security-state rr2-security-state--error">
        <strong>NVD lookup unavailable</strong>
        <span>{state.error}</span>
        <button className="rr2-btn rr2-btn--sm" type="button" onClick={() => setRefreshKey(value => value + 1)}>Retry</button>
      </div>
    );
  }

  const results = state.data?.results || [];
  const maxScore = results.reduce((highest, item) => Math.max(highest, item.best_score || 0), 0);
  const kevCount = results.filter(item => item.kev).length;

  return (
    <div className="rr2-security">
      <div className="rr2-security-query">
        <div><span>Live NVD query</span><strong>{query}</strong></div>
        <button className="rr2-btn rr2-btn--sm" type="button" onClick={() => setRefreshKey(value => value + 1)}>Refresh</button>
      </div>
      <div className="rr2-security-metrics">
        <div><strong>{state.data?.total_results || 0}</strong><span>Related CVEs</span></div>
        <div><strong>{maxScore || "None"}</strong><span>Highest CVSS</span></div>
        <div><strong>{kevCount}</strong><span>Known exploited</span></div>
      </div>
      {state.data?.warning && <p className="rr2-security-empty">{state.data.warning}</p>}
      <div className="rr2-cve-list">
        {results.map(item => (
          <article className="rr2-cve" key={item.cve_id}>
            <div className="rr2-cve__head">
              <a href={`https://nvd.nist.gov/vuln/detail/${item.cve_id}`} target="_blank" rel="noreferrer">{item.cve_id}</a>
              <span className={`rr2-cve__severity rr2-cve__severity--${String(item.severity || "unknown").toLowerCase()}`}>
                {item.severity || "Unscored"}{item.best_score != null ? ` ${item.best_score}` : ""}
              </span>
              {item.kev && <span className="rr2-cve__kev">KEV</span>}
            </div>
            <p>{item.description || "No English description supplied by NVD."}</p>
            <div className="rr2-cve__meta">
              <span>Published {item.published ? new Date(item.published).toLocaleDateString() : "unknown"}</span>
              <span>{item.metrics?.[0]?.source || "CVSS pending"}</span>
            </div>
            {item.affected_products?.length > 0 && (
              <details className="rr2-cve__products">
                <summary>Affected products ({item.affected_products.length})</summary>
                {item.affected_products.map(product => <code key={product}>{product}</code>)}
              </details>
            )}
          </article>
        ))}
      </div>
      <p className="rr2-security-source">{state.data?.cached ? "Cached for up to 15 minutes from" : "Live data from"} the NVD CVE API. Validate product and version applicability before acting.</p>
    </div>
  );
}

// ── Pill / Badge ────────────────────────────────────────────────────────────

function Pill({ children, variant = "neutral", small }) {
  return <span className={`rr2-pill rr2-pill--${variant}${small ? " rr2-pill--sm" : ""}`}>{children}</span>;
}

// ── Candidate Card ──────────────────────────────────────────────────────────

function CandidateCard({ candidate, isSelected, tier, onClick, showCheckbox, checked, onCheckChange }) {
  const n = candidate.normalized_rule_json || {};
  const warnings = deriveQualityWarnings(candidate);
  const headline = ruleHeadline(candidate);
  const summary = humanSummary(candidate);
  const page = candidate.source_page;
  const section = candidate.source_section;
  const isAutoApproved = tier === "auto";

  return (
    <div
      className={[
        "rr2-card",
        isSelected ? "rr2-card--selected" : "",
        candidate.review_status === "approved" ? "rr2-card--approved" : "",
        candidate.review_status === "rejected" ? "rr2-card--rejected" : "",
        isAutoApproved ? "rr2-card--auto" : "",
        tier === "individual" && warnings.length > 0 ? "rr2-card--flagged" : "",
      ].filter(Boolean).join(" ")}
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => { if (e.key === "Enter") onClick(); }}
    >
      {/* Top row */}
      <div className="rr2-card__top">
        {showCheckbox && (
          <input
            type="checkbox"
            className="rr2-card__check"
            checked={checked}
            onChange={e => { e.stopPropagation(); onCheckChange(candidate.candidate_id, e.target.checked); }}
            onClick={e => e.stopPropagation()}
          />
        )}
        <span className="rr2-card__headline">{headline}</span>
        <span className={`rr2-status ${statusClass(isAutoApproved ? "approved" : candidate.review_status)}`}>
          {isAutoApproved ? "Auto-approved" : statusLabel(candidate.review_status)}
        </span>
      </div>

      {/* Location row */}
      {(page || section) && (
        <div className="rr2-card__loc">
          {page && <span className="rr2-loc-page">Page {page}</span>}
          {section && <span className="rr2-loc-section">{section.length > 30 ? section.slice(0, 30) + "…" : section}</span>}
        </div>
      )}

      {/* Summary */}
      <p className="rr2-card__summary">{summary}</p>

      {/* Flag strip — individual tier only */}
      {tier === "individual" && warnings.length > 0 && (
        <div className="rr2-card__flag">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {warnings[0]}
        </div>
      )}

      {/* Footer meta */}
      <div className="rr2-card__footer">
        <span className={`rr2-conf rr2-conf--${confClass(candidate.confidence_score)}`}>
          {fmtConf(candidate.confidence_score)} confidence
        </span>
        {candidate.severity && <Pill variant={sevClass(candidate.severity)} small>{candidate.severity}</Pill>}
        {warnings.length > 1 && <Pill variant="warn" small>{warnings.length} warnings</Pill>}
      </div>
    </div>
  );
}

// ── Tier Lane ───────────────────────────────────────────────────────────────

function TierLane({ tier, title, subtitle, count, defaultExpanded, headerRight, accentClass, children }) {
  const [open, setOpen] = useState(defaultExpanded);
  return (
    <section className={`rr2-lane rr2-lane--${tier} ${accentClass}`}>
      <div className="rr2-lane__header" role="button" tabIndex={0}
        onClick={() => setOpen(v => !v)}
        onKeyDown={e => { if (e.key === "Enter") setOpen(v => !v); }}>
        <div className="rr2-lane__header-left">
          <div className={`rr2-lane__dot rr2-lane__dot--${tier}`} />
          <div>
            <div className="rr2-lane__title">{title}</div>
            {subtitle && <div className="rr2-lane__sub">{subtitle}</div>}
          </div>
          <span className="rr2-lane__count">{count}</span>
        </div>
        <div className="rr2-lane__header-right" onClick={e => e.stopPropagation()}>
          {headerRight}
          <button
            className="rr2-lane__toggle"
            onClick={e => { e.stopPropagation(); setOpen(v => !v); }}
            aria-label={open ? "Collapse" : "Expand"}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points={open ? "18 15 12 9 6 15" : "6 9 12 15 18 9"} />
            </svg>
          </button>
        </div>
      </div>
      {open && <div className="rr2-lane__body">{children}</div>}
    </section>
  );
}

// ── Structured Decision Panel ───────────────────────────────────────────────

function StructuredDecisionPanel({ candidate, onDecide, onInitiateReject }) {
  const prompt = getDecisionPrompt(candidate);
  return (
    <div className="rr2-sdp">
      <div className="rr2-sdp__banner">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        Individual review required
      </div>
      <p className="rr2-sdp__question">{prompt.question}</p>
      <div className="rr2-sdp__options">
        {prompt.options.map((opt, i) => (
          <button key={i}
            className={`rr2-sdp__opt rr2-sdp__opt--${opt.value}`}
            onClick={() => opt.value === "rejected" ? onInitiateReject(candidate.candidate_id) : onDecide(candidate.candidate_id, opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Rejection Reason Selector ───────────────────────────────────────────────

function RejectionReasonSelector({ onConfirm, onCancel }) {
  const [selected, setSelected] = useState("");
  const [otherText, setOtherText] = useState("");
  const reasons = getRejectionReasons();
  const canConfirm = selected !== "" && (selected !== "other" || otherText.trim().length > 0);
  const finalReason = selected === "other" ? otherText.trim() : selected;

  return (
    <div className="rr2-reject-panel">
      <p className="rr2-reject-panel__label">Why is this being rejected? (required)</p>
      <div className="rr2-reject-panel__options">
        {reasons.map(r => (
          <label key={r.value} className={`rr2-reject-option ${selected === r.value ? "rr2-reject-option--sel" : ""}`}>
            <input type="radio" name="rr" value={r.value} checked={selected === r.value} onChange={() => setSelected(r.value)} />
            {r.label}
          </label>
        ))}
      </div>
      {selected === "other" && (
        <input className="rr2-reject-panel__other" autoFocus
          placeholder="Describe the reason…" value={otherText} onChange={e => setOtherText(e.target.value)} />
      )}
      <div className="rr2-reject-panel__footer">
        <button className="rr2-btn rr2-btn--danger" disabled={!canConfirm} onClick={() => onConfirm(finalReason)}>
          Confirm Rejection
        </button>
        <button className="rr2-btn rr2-btn--ghost" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

// ── Standard Action Buttons (batch / auto tier) ─────────────────────────────

function StandardActions({ candidate, onUpdateReview, onInitiateReject }) {
  const s = candidate.review_status;
  return (
    <div className="rr2-std-actions">
      <div className="rr2-std-actions__label">Review Decision</div>
      <div className="rr2-std-actions__row">
        <button className={`rr2-btn rr2-btn--approve ${s === "approved" ? "rr2-btn--active" : ""}`}
          onClick={() => onUpdateReview(candidate.candidate_id, "approved")}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          Approve
        </button>
        <button className={`rr2-btn rr2-btn--reject ${s === "rejected" ? "rr2-btn--active" : ""}`}
          onClick={() => onInitiateReject(candidate.candidate_id)}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          Reject
        </button>
        <button className={`rr2-btn rr2-btn--clarify ${s === "needs_clarification" ? "rr2-btn--active" : ""}`}
          onClick={() => onUpdateReview(candidate.candidate_id, "needs_clarification")}>
          Needs Clarification
        </button>
        {s !== "pending_review" && (
          <button className="rr2-btn rr2-btn--ghost" onClick={() => onUpdateReview(candidate.candidate_id, "pending_review")}>
            Reset
          </button>
        )}
      </div>
      <p className="rr2-std-actions__note">
        Approved candidates are staged for downstream rule promotion.
      </p>
    </div>
  );
}

// ── Staged Confirmation ─────────────────────────────────────────────────────

function StagedConfirmationView({ candidates, onConfirmPromote, onGoBack }) {
  const approved = candidates.filter(c => c.review_status === "staged" || c.review_status === "approved").length;
  const rejected = candidates.filter(c => c.review_status === "rejected").length;
  const clarify  = candidates.filter(c => c.review_status === "needs_clarification").length;
  const auto     = candidates.filter(c => c.metadata_json?.auto_approved).length;

  return (
    <div className="rr2-staged">
      <div className="rr2-staged__icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div>
      <h2 className="rr2-staged__title">Ready to Promote</h2>
      <p className="rr2-staged__sub">Confirm the summary below before rules are handed off for compliance evaluation.</p>

      <div className="rr2-staged__grid">
        {[
          { label: "Approved for promotion", value: approved, cls: "success" },
          { label: "Auto-approved by system", value: auto,     cls: "info" },
          { label: "Rejected (not promoted)", value: rejected,  cls: "danger" },
          { label: "Needs clarification (deferred)", value: clarify, cls: "warn" },
        ].map(({ label, value, cls }) => (
          <div key={label} className={`rr2-staged__stat rr2-staged__stat--${cls}`}>
            <span className="rr2-staged__num">{value}</span>
            <span className="rr2-staged__lbl">{label}</span>
          </div>
        ))}
      </div>

      {clarify > 0 && (
        <div className="rr2-staged__note">
          ⓘ {clarify} candidate{clarify > 1 ? "s" : ""} marked "Needs Clarification" will not be promoted in this run.
        </div>
      )}

      <div className="rr2-staged__actions">
        <button className="rr2-promote-cta" onClick={onConfirmPromote}>
          Confirm and Promote Rules →
        </button>
        <button className="rr2-btn rr2-btn--ghost" onClick={onGoBack}>← Back to review</button>
      </div>
    </div>
  );
}

// ── Detail Panel ────────────────────────────────────────────────────────────

function DetailPanel({ candidate, tier, onUpdateReview, onInitiateReject, pendingRejectId, onConfirmRejection, onCancelRejection }) {
  const [tab, setTab] = useState("summary");

  useEffect(() => {
    if (!candidate) return;
    if (tier === "individual") {
      const p = getDecisionPrompt(candidate);
      setTab(p.defaultTab || "evidence");
    } else {
      setTab("summary");
    }
  }, [candidate?.candidate_id, tier]);

  if (!candidate) {
    return (
      <aside className="rr2-detail rr2-detail--empty">
        <div className="rr2-detail__empty">
          <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <strong>Select a rule to review</strong>
          <p>Click any card in the left panel to inspect its location, evidence, and normalized fields — then make a decision.</p>
        </div>
      </aside>
    );
  }

  const n = candidate.normalized_rule_json || {};
  const conditions   = Array.isArray(n.conditions)   ? n.conditions   : Array.isArray(candidate.conditions_json)   ? candidate.conditions_json   : [];
  const requirements = Array.isArray(n.requirements) ? n.requirements : Array.isArray(candidate.requirement_json)  ? candidate.requirement_json  : [];
  const warnings  = deriveQualityWarnings(candidate);
  const isRejectPending = pendingRejectId === candidate.candidate_id;
  const isAuto = tier === "auto";
  const isIndividual = tier === "individual";

  return (
    <aside className="rr2-detail">
      {/* Header */}
      <div className="rr2-detail__head">
        <div className="rr2-detail__head-left">
          <div className="rr2-detail__title">{ruleHeadline(candidate)}</div>
          <div className="rr2-detail__meta">
            <span className="rr2-detail__id">RCAND-{String(candidate.candidate_id).padStart(6, "0")}</span>
            {tier && <span className={`rr2-tier-chip rr2-tier-chip--${tier}`}>{tier}</span>}
          </div>
        </div>
        <span className={`rr2-status ${statusClass(isAuto ? "approved" : candidate.review_status)}`}>
          {isAuto ? "Auto-approved" : statusLabel(candidate.review_status)}
        </span>
      </div>

      {/* Location */}
      {(candidate.source_page || candidate.source_section) && (
        <div className="rr2-detail__location">
          <div className="rr2-detail__loc-label">Source location</div>
          <div className="rr2-detail__loc-chips">
            {candidate.source_page && (
              <span className="rr2-loc-chip rr2-loc-chip--page">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                Page {candidate.source_page}
              </span>
            )}
            {candidate.source_section && (
              <span className="rr2-loc-chip rr2-loc-chip--section">
                {candidate.source_section}
              </span>
            )}
            {candidate.source_chunk_type && candidate.source_chunk_type !== "prose" && (
              <span className="rr2-loc-chip rr2-loc-chip--type">{candidate.source_chunk_type.replace(/_/g, " ")}</span>
            )}
          </div>
        </div>
      )}

      {/* Evidence inline for individual tier */}
      {isIndividual && (
        <div className="rr2-detail__evidence-inline">
          <div className="rr2-detail__ev-label">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
            Source text from document
          </div>
          <blockquote className="rr2-quote rr2-quote--flagged">
            {candidate.source_excerpt || "No source excerpt available."}
          </blockquote>
        </div>
      )}

      {/* Tabs */}
      <div className="rr2-detail__tabs">
        {["summary", "evidence", "fields", "impact", "json"].map(t => (
          <button key={t} className={`rr2-detail__tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t === "impact" ? "Security Impact" : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="rr2-detail__body">

        {tab === "summary" && (
          <>
            <div className="rr2-detail__section">
              <div className="rr2-detail__sec-label">Plain-language summary</div>
              <p className="rr2-detail__summary">{humanSummary(candidate)}</p>
            </div>

            <div className="rr2-detail__section">
              <div className="rr2-detail__sec-label">AI confidence</div>
              <div className="rr2-conf-row">
                <div className="rr2-conf-track">
                  <div className={`rr2-conf-fill rr2-conf-fill--${confClass(candidate.confidence_score)}`}
                    style={{ width: `${Math.round((candidate.confidence_score || 0) * 100)}%` }} />
                </div>
                <span className={`rr2-conf-val rr2-conf-val--${confClass(candidate.confidence_score)}`}>
                  {fmtConf(candidate.confidence_score)}
                </span>
              </div>
              {candidate.confidence_reason && (
                <p className="rr2-conf-reason">{candidate.confidence_reason}</p>
              )}
            </div>

            {warnings.length > 0 && (
              <div className="rr2-detail__section rr2-warnings-box">
                <div className="rr2-detail__sec-label">Quality warnings</div>
                {warnings.map((w, i) => (
                  <div key={i} className="rr2-warning-row">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                    {w}
                  </div>
                ))}
              </div>
            )}

            {candidate.remediation_hint && (
              <div className="rr2-detail__section">
                <div className="rr2-detail__sec-label">Remediation hint</div>
                <p className="rr2-remediation">{candidate.remediation_hint || n.remediation_hint}</p>
              </div>
            )}
          </>
        )}

        {tab === "evidence" && (
          <div className="rr2-detail__section">
            <div className="rr2-detail__sec-label">Source excerpt</div>
            <blockquote className="rr2-quote">{candidate.source_excerpt || "No source excerpt available."}</blockquote>
            {candidate.source_section_path?.length > 0 && (
              <div className="rr2-section-path">
                {candidate.source_section_path.map((s, i) => <span key={i} className="rr2-section-path__item">{s}</span>)}
              </div>
            )}
          </div>
        )}

        {tab === "fields" && (
          <>
            {conditions.length > 0 && (
              <div className="rr2-detail__section">
                <div className="rr2-detail__sec-label">Conditions (when this rule applies)</div>
                <ul className="rr2-field-list">
                  {conditions.map((item, i) => <li key={i}>{readablePart(item)}</li>)}
                </ul>
              </div>
            )}
            {requirements.length > 0 && (
              <div className="rr2-detail__section">
                <div className="rr2-detail__sec-label">Requirements (what must be true)</div>
                <ul className="rr2-field-list">
                  {requirements.map((item, i) => <li key={i}>{readablePart(item)}</li>)}
                </ul>
              </div>
            )}
            {conditions.length === 0 && requirements.length === 0 && (
              <p className="rr2-no-data">No structured fields extracted.</p>
            )}
          </>
        )}

        {tab === "json" && (
          <div className="rr2-detail__section">
            <div className="rr2-detail__sec-label">Normalized JSON</div>
            <pre className="rr2-json">{JSON.stringify(n, null, 2)}</pre>
          </div>
        )}

        {tab === "impact" && <SecurityImpactPanel candidate={candidate} />}

      </div>

      {/* Decision area */}
      <div className="rr2-detail__foot">
        {isRejectPending ? (
          <RejectionReasonSelector
            onConfirm={(reason) => onConfirmRejection(candidate.candidate_id, reason)}
            onCancel={onCancelRejection}
          />
        ) : isIndividual ? (
          <StructuredDecisionPanel
            candidate={candidate}
            onDecide={(id, status) => onUpdateReview(id, status)}
            onInitiateReject={onInitiateReject}
          />
        ) : isAuto ? (
          <div className="rr2-auto-info">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            This rule was auto-approved (high confidence, no quality warnings). To override, use Reset to re-queue for manual review.
            <button className="rr2-btn rr2-btn--ghost rr2-auto-reset"
              onClick={() => onUpdateReview(candidate.candidate_id, "pending_review", { tier: "individual" })}>
              Override — move to manual review
            </button>
          </div>
        ) : (
          <StandardActions
            candidate={candidate}
            onUpdateReview={onUpdateReview}
            onInitiateReject={onInitiateReject}
          />
        )}
      </div>
    </aside>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function RuleReviewPage({
  document,
  candidates,
  selectedCandidate,
  onSelectCandidate,
  onUpdateReview,
  backendOnline,
  onRunPostReview,
  onRefreshCandidates,
}) {
  const [search, setSearch]           = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [pageFilter, setPageFilter]   = useState("all");
  const [groupBy, setGroupBy]         = useState("tier");

  const [autoApprovalDone, setAutoApprovalDone] = useState(false);
  const [autoApprovedCount, setAutoApprovedCount] = useState(0);

  const [pendingRejectId, setPendingRejectId] = useState(null);
  const [selectedIds, setSelectedIds]         = useState(new Set());
  const [showStaged, setShowStaged]           = useState(false);
  const [staging, setStaging]                 = useState(false);

  // ── Auto-approval ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (autoApprovalDone || candidates.length === 0 || !backendOnline) return;
    const pending = candidates.filter(c => c.review_status === "pending_review" && classifyRuleCandidate(c) === "auto");
    setAutoApprovalDone(true);
    if (pending.length === 0) return;
    const updates = pending.map(c => ({ candidate_id: c.candidate_id, review_status: "approved", tier: "auto", auto_approved: true }));
    candidateApi.bulkReview(updates)
      .then(() => { setAutoApprovedCount(pending.length); if (onRefreshCandidates) onRefreshCandidates(); })
      .catch(() => {});
  }, [candidates, autoApprovalDone, backendOnline]);

  // ── Tiering ───────────────────────────────────────────────────────────────
  const tiered = useMemo(() =>
    candidates.map(c => ({ ...c, _tier: classifyRuleCandidate(c) })),
    [candidates]
  );

  // ── Workload ──────────────────────────────────────────────────────────────
  const workload = useMemo(() => {
    const indiv = tiered.filter(c => c._tier === "individual");
    const batch = tiered.filter(c => c._tier === "batch");
    const auto  = tiered.filter(c => c._tier === "auto");
    const iP    = indiv.filter(c => c.review_status === "pending_review").length;
    const bP    = batch.filter(c => c.review_status === "pending_review").length;
    return {
      total: candidates.length,
      autoCount: autoApprovedCount || auto.filter(c => c.review_status === "approved").length,
      individualPending: iP,
      batchPending: bP,
      decisionsNeeded: iP + bP,
      allReviewed: iP === 0 && bP === 0,
    };
  }, [tiered, autoApprovedCount]);

  // ── Filters ───────────────────────────────────────────────────────────────
  const pages = useMemo(() => [...new Set(candidates.map(c => c.source_page).filter(Boolean))].sort((a, b) => a - b), [candidates]);

  const filtered = useMemo(() =>
    tiered.filter(c => {
      if (search && !JSON.stringify(c).toLowerCase().includes(search.toLowerCase())) return false;
      if (statusFilter !== "all" && c.review_status !== statusFilter) return false;
      if (pageFilter !== "all" && String(c.source_page) !== pageFilter) return false;
      return true;
    }),
    [tiered, search, statusFilter, pageFilter]
  );

  // ── Tier groups ───────────────────────────────────────────────────────────
  const individual = filtered.filter(c => c._tier === "individual");
  const batch      = filtered.filter(c => c._tier === "batch");
  const auto       = filtered.filter(c => c._tier === "auto");

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleUpdateReview = useCallback((candidateId, status, extra = {}) => {
    onUpdateReview(candidateId, status, extra);
  }, [onUpdateReview]);

  const handleInitiateReject = useCallback(id => setPendingRejectId(id), []);
  const handleConfirmRejection = useCallback((id, reason) => {
    setPendingRejectId(null);
    onUpdateReview(id, "rejected", { rejection_reason: reason });
  }, [onUpdateReview]);

  const handleCheckChange = useCallback((id, checked) => {
    setSelectedIds(prev => { const s = new Set(prev); checked ? s.add(id) : s.delete(id); return s; });
  }, []);

  const bulkAction = useCallback(async (items, status) => {
    const updates = items.filter(c => c.review_status === "pending_review").map(c => ({ candidate_id: c.candidate_id, review_status: status, tier: c._tier }));
    if (!updates.length) return;
    await candidateApi.bulkReview(updates).catch(() => {});
    setSelectedIds(new Set());
    if (onRefreshCandidates) onRefreshCandidates();
  }, [onRefreshCandidates]);

  const handleStage = useCallback(async () => {
    setStaging(true);
    const approved = candidates.filter(c => c.review_status === "approved");
    if (approved.length > 0) {
      await candidateApi.bulkReview(approved.map(c => ({ candidate_id: c.candidate_id, review_status: "staged" }))).catch(() => {});
      if (onRefreshCandidates) await onRefreshCandidates();
    }
    setStaging(false);
    setShowStaged(true);
  }, [candidates, onRefreshCandidates]);

  // ── Keyboard nav ──────────────────────────────────────────────────────────
  useEffect(() => {
    const flat = filtered;
    const idx  = selectedCandidate ? flat.findIndex(c => c.candidate_id === selectedCandidate.candidate_id) : -1;
    const handler = e => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === "n" || e.key === "N") { if (idx < flat.length - 1) onSelectCandidate(flat[idx + 1]); }
      if (e.key === "p" || e.key === "P") { if (idx > 0) onSelectCandidate(flat[idx - 1]); }
      if (e.key === "a" || e.key === "A") { if (selectedCandidate && deriveQualityWarnings(selectedCandidate).length === 0) handleUpdateReview(selectedCandidate.candidate_id, "approved"); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [filtered, selectedCandidate, onSelectCandidate, handleUpdateReview]);

  if (!document) return null;

  if (showStaged) {
    return (
      <div className="rr2-page">
        <StagedConfirmationView
          candidates={candidates}
          onConfirmPromote={() => { setShowStaged(false); onRunPostReview(); }}
          onGoBack={() => setShowStaged(false)}
        />
      </div>
    );
  }

  const selectedCount = selectedIds.size;
  const selCandidateTier = selectedCandidate ? classifyRuleCandidate(selectedCandidate) : null;

  return (
    <div className="rr2-page">

      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="rr2-header">
        <div className="rr2-header__left">
          <h2 className="rr2-header__title">Rule Review</h2>
          <p className="rr2-header__doc">{document.display_name || document.original_filename || document.document_id}</p>
        </div>
        <div className="rr2-header__right">
          <div className="rr2-kbd-hint" title="N / P = next/prev  ·  A = approve (no warnings)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            Keyboard shortcuts
          </div>
          <button className="rr2-promote-btn"
            disabled={!backendOnline || !workload.allReviewed || staging}
            title={!workload.allReviewed ? "Review all Batch and Individual rules first." : undefined}
            onClick={handleStage}>
            {staging ? "Staging…" : "Review Complete — Promote Rules →"}
          </button>
        </div>
      </div>

      {/* ── Workload dashboard ────────────────────────────────────────── */}
      <div className="rr2-dashboard">
        <div className="rr2-dashboard__primary">
          {workload.allReviewed ? (
            <div className="rr2-dashboard__done">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              All rules reviewed — ready to promote
            </div>
          ) : (
            <>
              <span className="rr2-dashboard__num">{workload.decisionsNeeded}</span>
              <span className="rr2-dashboard__label">decisions needed</span>
            </>
          )}
        </div>
        <div className="rr2-dashboard__stats">
          <div className="rr2-stat">
            <div className="rr2-stat__val">{workload.total}</div>
            <div className="rr2-stat__lbl">Total rules</div>
          </div>
          <div className="rr2-stat rr2-stat--green">
            <div className="rr2-stat__val">{workload.autoCount}</div>
            <div className="rr2-stat__lbl">Auto-approved</div>
          </div>
          <div className={`rr2-stat ${workload.batchPending > 0 ? "rr2-stat--amber" : ""}`}>
            <div className="rr2-stat__val">{workload.batchPending}</div>
            <div className="rr2-stat__lbl">Batch pending</div>
          </div>
          <div className={`rr2-stat ${workload.individualPending > 0 ? "rr2-stat--red" : ""}`}>
            <div className="rr2-stat__val">{workload.individualPending}</div>
            <div className="rr2-stat__lbl">Individual pending</div>
          </div>
        </div>
      </div>

      {/* ── Body split ───────────────────────────────────────────────── */}
      <div className="rr2-split">

        {/* Left — candidate list */}
        <div className="rr2-list-pane">

          {/* Filters */}
          <div className="rr2-filters">
            <div className="rr2-search">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input className="rr2-search__input" placeholder="Search rules…" value={search} onChange={e => setSearch(e.target.value)} />
              {search && <button className="rr2-search__clear" onClick={() => setSearch("")}>×</button>}
            </div>
            <div className="rr2-filter-row">
              <select className="rr2-sel" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                <option value="all">All statuses</option>
                <option value="pending_review">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="needs_clarification">Needs Clarification</option>
                <option value="staged">Staged</option>
              </select>
              {pages.length > 1 && (
                <select className="rr2-sel" value={pageFilter} onChange={e => setPageFilter(e.target.value)}>
                  <option value="all">All pages</option>
                  {pages.map(p => <option key={p} value={String(p)}>Page {p}</option>)}
                </select>
              )}
              <select className="rr2-sel" value={groupBy} onChange={e => setGroupBy(e.target.value)}>
                <option value="tier">By Tier</option>
                <option value="page">By Page</option>
                <option value="status">By Status</option>
              </select>
            </div>
            <div className="rr2-filters__count">{filtered.length} of {candidates.length} rules shown</div>
          </div>

          {/* Candidates */}
          <div className="rr2-scroll">
            {candidates.length === 0 ? (
              <div className="rr2-empty">
                <strong>No rule candidates yet</strong>
                <p>Run the pipeline extraction stages first.</p>
              </div>
            ) : filtered.length === 0 ? (
              <div className="rr2-empty rr2-empty--sm">
                <strong>No matches</strong>
                <p>Adjust your filters.</p>
              </div>
            ) : groupBy === "tier" ? (
              <div className="rr2-lanes">

                {/* ── INDIVIDUAL ─── */}
                {individual.length > 0 && (
                  <TierLane
                    tier="individual"
                    title="⚠ Individual Review Required"
                    subtitle="Flagged for human judgment — AI confidence is low or extraction is uncertain"
                    count={individual.length}
                    defaultExpanded={true}
                    accentClass="rr2-lane--accent-red"
                    headerRight={null}
                  >
                    {individual.map(c => (
                      <CandidateCard key={c.candidate_id} candidate={c} tier="individual"
                        isSelected={selectedCandidate?.candidate_id === c.candidate_id}
                        onClick={() => onSelectCandidate(c)}
                        showCheckbox={false} checked={false} onCheckChange={() => {}} />
                    ))}
                  </TierLane>
                )}

                {/* ── BATCH ─── */}
                {batch.length > 0 && (
                  <TierLane
                    tier="batch"
                    title="⚡ Batch Review"
                    subtitle="Solid confidence — approve or clarify as a group, or check individually"
                    count={batch.length}
                    defaultExpanded={true}
                    accentClass="rr2-lane--accent-amber"
                    headerRight={
                      <div className="rr2-lane-bulk-btns">
                        <button className="rr2-btn rr2-btn--sm rr2-btn--approve" onClick={() => bulkAction(batch, "approved")}>Approve all</button>
                        <button className="rr2-btn rr2-btn--sm rr2-btn--clarify" onClick={() => bulkAction(batch, "needs_clarification")}>Clarify all</button>
                      </div>
                    }
                  >
                    {batch.map(c => (
                      <CandidateCard key={c.candidate_id} candidate={c} tier="batch"
                        isSelected={selectedCandidate?.candidate_id === c.candidate_id}
                        onClick={() => onSelectCandidate(c)}
                        showCheckbox={true}
                        checked={selectedIds.has(c.candidate_id)}
                        onCheckChange={handleCheckChange} />
                    ))}
                  </TierLane>
                )}

                {/* ── AUTO APPROVED ─── always shown ─── */}
                <TierLane
                  tier="auto"
                  title="✓ Auto-Approved"
                  subtitle={`${auto.length} rule${auto.length !== 1 ? "s" : ""} met all high-confidence thresholds and were approved automatically`}
                  count={auto.length}
                  defaultExpanded={true}
                  accentClass="rr2-lane--accent-green"
                  headerRight={null}
                >
                  {auto.length === 0 ? (
                    <p className="rr2-lane-empty">No rules qualify for auto-approval in this document (requires confidence ≥ 93%, no quality warnings, hard enforcement).</p>
                  ) : (
                    auto.map(c => (
                      <CandidateCard key={c.candidate_id} candidate={c} tier="auto"
                        isSelected={selectedCandidate?.candidate_id === c.candidate_id}
                        onClick={() => onSelectCandidate(c)}
                        showCheckbox={false} checked={false} onCheckChange={() => {}} />
                    ))
                  )}
                </TierLane>

              </div>
            ) : (
              /* Page / Status grouping */
              (() => {
                const groups = {};
                filtered.forEach(c => {
                  const key = groupBy === "page" ? (c.source_page ? `Page ${c.source_page}` : "Unknown Page") : (c.review_status || "pending_review");
                  if (!groups[key]) groups[key] = [];
                  groups[key].push(c);
                });
                return Object.entries(groups).map(([label, items]) => (
                  <div key={label} className="rr2-group">
                    <div className="rr2-group__hdr">
                      <span>{groupBy === "status" ? statusLabel(label) : label}</span>
                      <span className="rr2-group__count">{items.length}</span>
                    </div>
                    {items.map(c => (
                      <CandidateCard key={c.candidate_id} candidate={c} tier={c._tier}
                        isSelected={selectedCandidate?.candidate_id === c.candidate_id}
                        onClick={() => onSelectCandidate(c)}
                        showCheckbox={false} checked={false} onCheckChange={() => {}} />
                    ))}
                  </div>
                ));
              })()
            )}
          </div>

          {/* Multi-select action bar */}
          {selectedCount > 0 && (
            <div className="rr2-multisel-bar">
              <span><strong>{selectedCount}</strong> selected</span>
              <button className="rr2-btn rr2-btn--approve rr2-btn--sm"
                onClick={() => bulkAction(batch.filter(c => selectedIds.has(c.candidate_id)), "approved")}>
                Approve selected
              </button>
              <button className="rr2-btn rr2-btn--clarify rr2-btn--sm"
                onClick={() => bulkAction(batch.filter(c => selectedIds.has(c.candidate_id)), "needs_clarification")}>
                Clarify selected
              </button>
              <button className="rr2-btn rr2-btn--ghost rr2-btn--sm" onClick={() => setSelectedIds(new Set())}>Clear</button>
            </div>
          )}
        </div>

        {/* Right — detail */}
        <DetailPanel
          candidate={selectedCandidate}
          tier={selCandidateTier}
          onUpdateReview={handleUpdateReview}
          onInitiateReject={handleInitiateReject}
          pendingRejectId={pendingRejectId}
          onConfirmRejection={handleConfirmRejection}
          onCancelRejection={() => setPendingRejectId(null)}
        />
      </div>
    </div>
  );
}
