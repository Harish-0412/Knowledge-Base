import React from "react";
import { documentApi } from "../../lib/api";

function numberOrDash(v) {
  return v === undefined || v === null ? "—" : v;
}

const STAGES = [
  {
    key: "profile",
    label: "Document Profile",
    description: "Detects document type, page layout, parser strategy, and extraction route per page.",
    doneKey: "profiled",
    outputKey: null,
    outputLabel: null,
    run: documentApi.profile,
  },
  {
    key: "extract",
    label: "Evidence Extraction",
    description: "Runs Docling / PyMuPDF / OCR extraction, creates semantic chunks, tables, and evidence objects.",
    doneKey: "extracted",
    outputKey: "chunks",
    outputLabel: "chunks extracted",
    run: documentApi.extract,
  },
  {
    key: "rules",
    label: "Rule Candidate Extraction",
    description: "Identifies compatibility constraints and requirements from tables and rule-bearing text.",
    doneKey: "rules_extracted",
    outputKey: "raw_candidates",
    outputLabel: "rule candidates found",
    run: documentApi.extractRules,
  },
  {
    key: "normalize",
    label: "Normalization & Quality",
    description: "Converts raw candidates into structured conditions, requirements, versions, and source evidence.",
    doneKey: "normalized",
    outputKey: "normalized_candidates",
    outputLabel: "normalized",
    run: documentApi.normalizeCandidates,
  },
  {
    key: "review",
    label: "Ready for Rule Review",
    description: "Pipeline complete. Rule candidates are ready for human review and approval.",
    doneKey: "review_started",
    outputKey: "pending_review",
    outputLabel: "pending your review",
    run: null,
  },
];

// ── Stage Row ─────────────────────────────────────────────────────────────

function StageRow({
  stage,
  index,
  isDone,
  isActive,   // ← the currently processing stage (first incomplete one while busy)
  isBusy,
  backendOnline,
  summary,
  onRunStage,
  onGoToReview,
}) {
  const counts = summary?.counts || {};
  const value = stage.outputKey ? counts[stage.outputKey] : null;

  // visual state
  const state = isActive ? "running" : isDone ? "done" : "pending";

  return (
    <div className={`pip-stage pip-stage--${state}`}>
      {/* Vertical connector line between stages */}
      <div className="pip-stage-connector" />

      {/* Circle marker */}
      <div className="pip-stage-marker">
        {isActive ? (
          <span className="pip-stage-spinner" />
        ) : isDone ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <span className="pip-stage-num">{index + 1}</span>
        )}
      </div>

      {/* Stage content card */}
      <div className="pip-stage-content">
        <div className="pip-stage-header">
          <div className="pip-stage-title-block">
            <h3 className="pip-stage-title">{stage.label}</h3>
            {/* "Processing…" text label under the title while this stage is active */}
            {isActive && (
              <span className="pip-stage-processing-label">
                <span className="pip-stage-processing-dot" />
                Processing…
              </span>
            )}
          </div>

          <div className="pip-stage-right">
            {/* Output count once done */}
            {value != null && isDone && (
              <span className="pip-stage-output">
                {value} {stage.outputLabel}
              </span>
            )}

            {/* Go to review button */}
            {stage.key === "review" && isDone && (
              <button className="primary-button pip-go-review-btn" onClick={onGoToReview}>
                Go to Rule Review →
              </button>
            )}

            {/* Run step (not done, not running) */}
            {stage.run && !isDone && !isActive && (
              <button
                className="secondary-button pip-run-btn"
                disabled={isBusy || !backendOnline}
                onClick={() => onRunStage(stage.key, stage.run)}
              >
                {isBusy ? "Busy…" : "Run Step"}
              </button>
            )}

            {/* Re-run (done but can redo) */}
            {stage.run && isDone && !isActive && (
              <button
                className="link-button pip-rerun-btn"
                disabled={isBusy || !backendOnline}
                onClick={() => onRunStage(stage.key, stage.run)}
              >
                Re-run
              </button>
            )}
          </div>
        </div>
        <p className="pip-stage-desc">{stage.description}</p>
      </div>
    </div>
  );
}

// ── Main Pipeline Page ─────────────────────────────────────────────────────

export default function DocumentPipelinePage({
  document,
  summary,
  busyStage,     // truthy when any stage is running (the key name, e.g. "Run Full Pipeline")
  backendOnline,
  onRunStage,
  onGoToReview,
  onStartPipeline,
}) {
  const pipeline = summary?.pipeline || {};
  const counts = summary?.counts || {};

  // ── Determine which stages are done ────────────────────────────────────
  const stageDone = {
    profile:   !!(pipeline.profiled),
    extract:   !!(pipeline.extracted || pipeline.evidence_extracted),
    rules:     !!(pipeline.rules_extracted),
    normalize: !!(pipeline.normalized),
    review:    !!(counts.rule_candidates > 0),
  };

  const allDone     = STAGES.every(s => stageDone[s.key]);
  const noneStarted = !Object.values(stageDone).some(Boolean);

  // ── Active stage: first incomplete stage while pipeline is busy ──────
  // This means regardless of WHICH runStage key triggered the run, the visual
  // "spinning" stage is always the next one that hasn't been completed yet.
  // This survives navigation because we restore busyStage from sessionStorage.
  const activeStageIndex = busyStage
    ? STAGES.findIndex(s => !stageDone[s.key])
    : -1;

  if (!document) return null;

  const displayName =
    document.display_name ||
    document.original_filename ||
    document.filename ||
    document.document_id;

  const fileType = (document.file_type || "FILE").split("/").pop().toUpperCase().slice(0, 4);

  return (
    <div className="pip-page">
      {/* ── Document header ─────────────────────────────────────────── */}
      <div className="pip-doc-header">
        <div className="pip-doc-header-left">
          <div className="pip-doc-file-badge">{fileType}</div>
          <div>
            <h2 className="pip-doc-name">{displayName}</h2>
            <span className="pip-doc-id">{document.document_id}</span>
          </div>
        </div>

        <div className="pip-doc-header-right">
          {/* Start button — only when nothing has run yet */}
          {noneStarted && !busyStage && (
            <button
              className="primary-button pip-start-btn"
              disabled={!backendOnline}
              onClick={onStartPipeline}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 7 }}>
                <circle cx="12" cy="12" r="10" />
                <polygon points="10 8 16 12 10 16 10 8" />
              </svg>
              Start Document Intelligence
            </button>
          )}

          {/* Running state header button */}
          {busyStage && (
            <button className="primary-button pip-start-btn pip-start-btn--running" disabled>
              <span className="btn-spinner" style={{ marginRight: 8 }} />
              Pipeline Running…
            </button>
          )}

          {/* Partial pipeline done, nothing running */}
          {!noneStarted && !allDone && !busyStage && (
            <button
              className="secondary-button pip-start-btn"
              disabled={!backendOnline}
              onClick={onStartPipeline}
            >
              Run Full Pipeline
            </button>
          )}

          {/* All done */}
          {allDone && !busyStage && (
            <button className="primary-button pip-start-btn" onClick={onGoToReview}>
              Go to Rule Review →
            </button>
          )}
        </div>
      </div>

      {/* ── Live processing banner ──────────────────────────────────── */}
      {busyStage && (
        <div className="pip-running-banner">
          <span className="pip-running-dot" />
          <div>
            <strong>Pipeline is running</strong>
            <span style={{ opacity: .75, marginLeft: 8 }}>
              — This page auto-updates every few seconds. You can navigate away and come back — your progress is saved.
            </span>
          </div>
        </div>
      )}

      {/* ── Sequential stepper ─────────────────────────────────────── */}
      <div className="pip-stepper">
        {STAGES.map((stage, i) => (
          <StageRow
            key={stage.key}
            stage={stage}
            index={i}
            isDone={!!stageDone[stage.key]}
            isActive={i === activeStageIndex}
            isBusy={!!busyStage}
            backendOnline={backendOnline}
            summary={summary}
            onRunStage={onRunStage}
            onGoToReview={onGoToReview}
          />
        ))}
      </div>

      {/* ── Stats summary when data available ──────────────────────── */}
      {counts.chunks > 0 && (
        <div className="pip-stats-grid">
          {[
            ["Chunks / Evidence", counts.chunks],
            ["Rule Candidates", counts.rule_candidates ?? counts.raw_candidates],
            ["Normalized", counts.normalized_candidates],
            ["Pending Review", counts.pending_review],
            ["Approved", counts.approved_for_next_stage],
            ["Quality Warnings", counts.quality_warnings],
          ].map(([label, value]) => (
            <div key={label} className="pip-stat-card">
              <span className="pip-stat-label">{label}</span>
              <strong className="pip-stat-value">{numberOrDash(value)}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
