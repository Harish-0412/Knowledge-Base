import React from "react";

const EXPECTED_EXPORTS = [
  ["chunks", "Evidence Chunks"],
  ["chunks_csv", "Chunks CSV"],
  ["raw_rule_candidates", "Raw Rule Candidates"],
  ["normalized_rule_candidates", "Normalized Candidates"],
  ["candidate_quality_report", "Quality Report"],
  ["pipeline_summary", "Pipeline Summary"],
  ["llm_call_log", "LLM Call Log"],
  ["processing_lane_report", "Processing Lane Report"],
];

function numberOrDash(v) {
  return v === undefined || v === null ? "—" : v;
}

function formatConfidence(v) {
  return v == null ? "—" : `${Math.round(v * 100)}%`;
}

function Field({ label, value }) {
  return (
    <div className="di-field">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

export default function HandoffPage({ document, summary, candidates, exportsMap, qualityReport }) {
  if (!document) return null;

  const counts = summary?.counts || {};
  const approved = candidates.filter(c => c.review_status === "approved");
  const rejected = candidates.filter(c => c.review_status === "rejected");
  const pending = candidates.filter(c => c.review_status === "pending_review");
  const clarify = candidates.filter(c => c.review_status === "needs_clarification");
  const readyForHandoff = approved.length > 0 && pending.length === 0;

  return (
    <div className="hoff-page">
      <div className="hoff-page-header">
        <div>
          <h2 className="hoff-title">Handoff Package</h2>
          <p className="hoff-sub">Reviewed candidates and export files for downstream teammate layers</p>
        </div>
        <span className={`badge ${readyForHandoff ? "success" : "warning"}`}>
          {readyForHandoff ? "Ready for Handoff" : "Review Incomplete"}
        </span>
      </div>

      {/* Summary cards */}
      <div className="hoff-summary-grid">
        <div className="hoff-summary-card">
          <span className="hoff-summary-label">Normalized Candidates</span>
          <strong className="hoff-summary-val">{numberOrDash(counts.normalized_candidates)}</strong>
        </div>
        <div className="hoff-summary-card success">
          <span className="hoff-summary-label">Approved for Next Stage</span>
          <strong className="hoff-summary-val">{approved.length}</strong>
        </div>
        <div className="hoff-summary-card warning">
          <span className="hoff-summary-label">Pending Review</span>
          <strong className="hoff-summary-val">{pending.length}</strong>
        </div>
        <div className="hoff-summary-card error">
          <span className="hoff-summary-label">Rejected</span>
          <strong className="hoff-summary-val">{rejected.length}</strong>
        </div>
        <div className="hoff-summary-card info">
          <span className="hoff-summary-label">Needs Clarification</span>
          <strong className="hoff-summary-val">{clarify.length}</strong>
        </div>
        <div className="hoff-summary-card">
          <span className="hoff-summary-label">Quality Warnings</span>
          <strong className="hoff-summary-val">{numberOrDash(counts.quality_warnings)}</strong>
        </div>
      </div>

      {/* Approved candidates table */}
      {approved.length > 0 && (
        <section className="panel hoff-panel">
          <div className="panel-header">
            <div>
              <h2>Approved Candidates</h2>
              <p>{approved.length} candidate{approved.length !== 1 ? "s" : ""} approved for next stage</p>
            </div>
          </div>
          <div className="hoff-table">
            <div className="hoff-table-head">
              <span>ID</span>
              <span>Rule Type</span>
              <span>Page</span>
              <span>Section</span>
              <span>Confidence</span>
              <span>Severity</span>
            </div>
            {approved.map(c => (
              <div key={c.candidate_id} className="hoff-table-row">
                <span className="hoff-mono">RCAND-{String(c.candidate_id).padStart(6, "0")}</span>
                <span>{c.rule_type || c.normalized_rule_json?.rule_type || "—"}</span>
                <span>{c.source_page ? `Page ${c.source_page}` : "—"}</span>
                <span className="hoff-section">{c.source_section || "—"}</span>
                <span>{formatConfidence(c.confidence_score)}</span>
                <span>{c.severity || "—"}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {approved.length === 0 && (
        <div className="hoff-notice">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          No candidates approved yet. Go to Rule Review to approve candidates for handoff.
        </div>
      )}

      {/* Export files */}
      <section className="panel hoff-panel">
        <div className="panel-header">
          <div>
            <h2>Export Files</h2>
            <p>Generated files for review, debugging, and teammate handoff</p>
          </div>
        </div>
        <div className="hoff-export-grid">
          {EXPECTED_EXPORTS.map(([name, label]) => {
            const item = exportsMap?.[name];
            const exists = item?.exists;
            return (
              <div key={name} className={`hoff-export-card ${exists ? "exists" : "missing"}`}>
                <div className="hoff-export-card-head">
                  <span className="hoff-export-icon">
                    {exists ? (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                    ) : (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/></svg>
                    )}
                  </span>
                  <strong>{label}</strong>
                  <span className={`badge ${exists ? "success" : "neutral"}`}>{exists ? "Generated" : "Pending"}</span>
                </div>
                {exists && item?.path && <p className="hoff-export-path">{item.path}</p>}
              </div>
            );
          })}
        </div>
      </section>

      {/* API Contract */}
      <section className="panel hoff-panel">
        <div className="panel-header">
          <div>
            <h2>API Contract for Teammates</h2>
            <p>Current Document Intelligence handoff endpoints</p>
          </div>
        </div>
        <div className="hoff-contract-list">
          {[
            ["GET", "/api/documents", "List uploaded source documents"],
            ["GET", "/api/documents/{id}", "Document metadata and current status"],
            ["GET", "/api/documents/{id}/intelligence-summary", "Counts, quality, pipeline, and export summary"],
            ["GET", "/api/documents/{id}/chunks", "Extracted evidence chunks"],
            ["GET", "/api/documents/{id}/rule-candidates", "Enriched candidates with page, section, and zone location"],
            ["GET", "/api/rule-candidates/{id}", "One candidate with raw and normalized payloads"],
            ["PATCH", "/api/rule-candidates/{id}/review", "Update candidate review status"],
            ["GET", "/api/documents/{id}/exports", "Generated handoff file status"],
          ].map(([method, path, desc]) => (
            <div key={path} className="hoff-contract-row">
              <span className={`hoff-method hoff-method--${method.toLowerCase()}`}>{method}</span>
              <code className="hoff-path">{path}</code>
              <span className="hoff-desc">{desc}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
