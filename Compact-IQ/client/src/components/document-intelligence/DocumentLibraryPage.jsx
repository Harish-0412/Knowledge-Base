import React, { useRef, useState, useMemo } from "react";
import { documentApi } from "../../lib/api";

const STATUS_META = {
  uploaded:          { label: "Uploaded — not started",    tone: "neutral",  dot: 0 },
  profiled:          { label: "Profiled",                   tone: "info",     dot: 1 },
  extracted:         { label: "Evidence extracted",         tone: "info",     dot: 2 },
  rules_extracted:   { label: "Rules extracted",            tone: "warning",  dot: 3 },
  normalized:        { label: "Ready for review",           tone: "success",  dot: 4 },
  ready_for_review:  { label: "Ready for review",           tone: "success",  dot: 4 },
  processing:        { label: "Processing…",                tone: "warning",  dot: -1 },
  failed:            { label: "Processing failed",          tone: "error",    dot: -1 },
};

const PIPELINE_STAGES = ["Profile", "Extract", "Rules", "Normalize", "Review"];

function fileTypeLabel(doc) {
  const v = doc?.file_type || doc?.content_type || doc?.source_type || "";
  if (v.includes("pdf")) return "PDF";
  if (v.includes("csv")) return "CSV";
  if (v.includes("text") || v.includes("txt")) return "TXT";
  return v ? v.toUpperCase().slice(0, 4) : "File";
}

function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  return isNaN(d) ? value : d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function formatSize(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function displayName(doc) {
  return doc?.display_name || doc?.original_filename || doc?.filename || doc?.document_id || "Untitled";
}

// ── Pipeline dots strip on each card ─────────────────────────────────────

function PipelineDots({ status }) {
  const meta = STATUS_META[status] || { dot: 0 };
  const filled = meta.dot;
  const failed = status === "failed";
  return (
    <div className="lib-pipeline-dots">
      {PIPELINE_STAGES.map((stage, i) => (
        <span
          key={stage}
          className={`lib-pipeline-dot ${
            failed ? "error" : i < filled ? "done" : i === filled ? "active" : ""
          }`}
          title={stage}
        />
      ))}
    </div>
  );
}

// ── Upload modal ──────────────────────────────────────────────────────────

function UploadModal({ backendOnline, onUploaded, onClose }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  };

  const upload = async () => {
    if (!file) { setError("Select a file first."); return; }
    setUploading(true); setError("");
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);
      const doc = await documentApi.upload(fd);
      onUploaded(doc);
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal lib-upload-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="lib-upload-modal-title">
            <div className="lib-upload-modal-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <div>
              <h2>Upload Document</h2>
              <p>The pipeline will start automatically after upload</p>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="lib-upload-body">
          <div
            className={`lib-drop-zone ${dragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <input ref={fileRef} type="file" hidden accept=".pdf,.csv,.txt" onChange={e => setFile(e.target.files?.[0] || null)} />
            {file ? (
              <>
                <div className="lib-drop-file-icon">
                  {file.name.split(".").pop().toUpperCase().slice(0, 4)}
                </div>
                <strong className="lib-drop-filename">{file.name}</strong>
                <span className="lib-drop-size">{formatSize(file.size)}</span>
                <button className="link-button lib-drop-change" onClick={e => { e.stopPropagation(); setFile(null); }}>
                  Choose a different file
                </button>
              </>
            ) : (
              <>
                <div className="lib-drop-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/>
                  </svg>
                </div>
                <strong>Drop a file here or click to browse</strong>
                <span>PDF, CSV, or TXT — vendor release notes, compatibility matrices, rollout docs</span>
              </>
            )}
          </div>

          {error && <div className="di-alert error">{error}</div>}

          <div className="lib-upload-hint">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            After upload, you'll be taken into the pipeline view and processing will start automatically.
          </div>
        </div>

        <div className="modal-footer">
          <button className="secondary-button" onClick={onClose}>Cancel</button>
          <button className="primary-button" onClick={upload} disabled={uploading || !backendOnline || !file}>
            {uploading ? (
              <><span className="btn-spinner" /> Uploading…</>
            ) : "Upload & Start Pipeline"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Library Page ─────────────────────────────────────────────────────

export default function DocumentLibraryPage({
  backendOnline,
  documents,
  summaries,
  globalPipelineRunning,   // boolean — any pipeline currently running
  globalPipelineDocId,     // documentId of the running pipeline (for the warning message)
  onSelectDocument,
  onRunPipeline,           // click "Run Pipeline" on a card → navigate + auto-start
  onUploaded,
}) {
  const [showUpload, setShowUpload] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = useMemo(() => {
    return [...documents]
      .filter(doc => {
        const name = displayName(doc).toLowerCase();
        const id = doc.document_id.toLowerCase();
        if (search && !name.includes(search.toLowerCase()) && !id.includes(search.toLowerCase())) return false;
        if (statusFilter !== "all" && doc.status !== statusFilter) return false;
        return true;
      })
      .sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at));
  }, [documents, search, statusFilter]);

  const uniqueStatuses = [...new Set(documents.map(d => d.status))];

  // Whether a card should allow "Run Pipeline"
  const canRunPipeline = (doc) => {
    // Can run if status is uploaded or partially processed (not already done)
    const terminal = ["normalized", "ready_for_review"];
    return !terminal.includes(doc.status) && doc.status !== "processing";
  };

  const isThisRunning = (doc) => globalPipelineDocId === doc.document_id && globalPipelineRunning;

  return (
    <div className="lib-page">
      {showUpload && (
        <UploadModal
          backendOnline={backendOnline}
          onClose={() => setShowUpload(false)}
          onUploaded={(doc) => {
            setShowUpload(false);
            onUploaded(doc);
          }}
        />
      )}

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="lib-hero">
        <div className="lib-hero-text">
          <h2 className="lib-hero-title">Document Intelligence</h2>
          <p className="lib-hero-sub">
            Upload vendor release notes, compatibility matrices, rollout PDFs, or firmware docs.
            Each document gets its own processing pipeline — extract evidence, generate rule candidates, and review them for handoff.
          </p>
        </div>
        <button
          className="primary-button lib-upload-btn"
          onClick={() => setShowUpload(true)}
          disabled={!backendOnline}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 7, verticalAlign: "middle" }}>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          {backendOnline ? "Upload Document" : "Backend Offline"}
        </button>
      </section>

      {/* ── Global pipeline-running notice ────────────────────────────── */}
      {globalPipelineRunning && globalPipelineDocId && (
        <div className="lib-pipeline-active-notice">
          <span className="pip-running-dot" />
          <div>
            <strong>Pipeline is running</strong>
            <span style={{ marginLeft: 8, opacity: .8 }}>
              Document <code style={{ fontSize: 11 }}>{globalPipelineDocId}</code> is currently processing.
              You cannot start another pipeline until this one completes.
            </span>
          </div>
          <button
            className="secondary-button lib-notice-view-btn"
            onClick={() => {
              const doc = documents.find(d => d.document_id === globalPipelineDocId);
              if (doc) onSelectDocument(doc);
            }}
          >
            View Pipeline →
          </button>
        </div>
      )}

      {/* ── Stats strip ───────────────────────────────────────────────── */}
      {documents.length > 0 && (
        <div className="lib-stats-strip">
          {[
            { label: "Total Documents", value: documents.length, tone: "" },
            { label: "Ready for Review", value: documents.filter(d => ["normalized","ready_for_review","rules_extracted"].includes(d.status)).length, tone: "success" },
            { label: "Processing", value: documents.filter(d => ["profiled","extracted","processing"].includes(d.status)).length, tone: "warning" },
            { label: "Failed", value: documents.filter(d => d.status === "failed").length, tone: "error" },
          ].map(({ label, value, tone }) => (
            <div key={label} className={`lib-stat-card ${tone}`}>
              <span className="lib-stat-value">{value}</span>
              <span className="lib-stat-label">{label}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Toolbar ───────────────────────────────────────────────────── */}
      {documents.length > 0 && (
        <div className="lib-toolbar">
          <div className="lib-search-wrap">
            <svg className="lib-search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              className="lib-search"
              placeholder="Search by name or document ID…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && (
              <button className="lib-search-clear" onClick={() => setSearch("")}>×</button>
            )}
          </div>
          <select className="lib-filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="all">All statuses</option>
            {uniqueStatuses.map(s => (
              <option key={s} value={s}>{STATUS_META[s]?.label || s}</option>
            ))}
          </select>
          <span className="lib-count">{filtered.length} document{filtered.length !== 1 ? "s" : ""}</span>
        </div>
      )}

      {/* ── Document Grid ─────────────────────────────────────────────── */}
      {documents.length === 0 ? (
        <div className="lib-empty">
          <div className="lib-empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/>
            </svg>
          </div>
          <h3>No documents yet</h3>
          <p>Upload a vendor document to start your first Document Intelligence pipeline.</p>
          <button className="primary-button" onClick={() => setShowUpload(true)} disabled={!backendOnline}>
            Upload Your First Document
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="lib-empty compact">
          <h3>No matching documents</h3>
          <p>Adjust your search or status filter.</p>
          <button className="secondary-button" onClick={() => { setSearch(""); setStatusFilter("all"); }}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="lib-grid">
          {filtered.map(doc => {
            const summary = summaries[doc.document_id];
            const meta = STATUS_META[doc.status] || { label: doc.status, tone: "neutral", dot: 0 };
            const counts = summary?.counts || {};
            const running = isThisRunning(doc);

            return (
              <article key={doc.document_id} className={`lib-card ${running ? "lib-card--running" : ""}`}>
                <div className="lib-card-head">
                  <div className="lib-card-file-icon">{fileTypeLabel(doc)}</div>
                  <div className="lib-card-title-block">
                    <h3 className="lib-card-name">{displayName(doc)}</h3>
                    <span className="lib-card-id">{doc.document_id}</span>
                  </div>
                  {running ? (
                    <span className="badge warning lib-card-running-badge">
                      <span className="pip-running-dot" style={{ width: 6, height: 6, marginRight: 4 }} />
                      Processing
                    </span>
                  ) : (
                    <span className={`badge ${meta.tone}`}>{meta.label}</span>
                  )}
                </div>

                <PipelineDots status={running ? "processing" : doc.status} />

                <div className="lib-card-meta">
                  <span>{fileTypeLabel(doc)}</span>
                  <span>{formatSize(doc.file_size_bytes)}</span>
                  <span>Uploaded {formatDate(doc.uploaded_at)}</span>
                </div>

                {(counts.rule_candidates > 0 || counts.chunks > 0) && (
                  <div className="lib-card-counts">
                    {counts.chunks > 0 && <span>{counts.chunks} chunks</span>}
                    {counts.rule_candidates > 0 && <span>{counts.rule_candidates} rule candidates</span>}
                    {counts.pending_review > 0 && <span className="pending">{counts.pending_review} pending review</span>}
                    {counts.approved_for_next_stage > 0 && <span className="approved">{counts.approved_for_next_stage} approved</span>}
                  </div>
                )}

                {/* ── Card Actions ───────────────────────────────────── */}
                <div className="lib-card-actions">
                  {running ? (
                    /* If this doc is running — single "View Pipeline" button */
                    <button
                      className="primary-button lib-card-open"
                      onClick={() => onSelectDocument(doc)}
                    >
                      <span className="btn-spinner" style={{ marginRight: 6 }} />
                      View Running Pipeline →
                    </button>
                  ) : canRunPipeline(doc) ? (
                    /* Not started / partially done → show both Open + Run */
                    <div className="lib-card-dual-actions">
                      <button
                        className="secondary-button lib-card-view-btn"
                        onClick={() => onSelectDocument(doc)}
                      >
                        Open
                      </button>
                      <button
                        className="primary-button lib-card-run-btn"
                        disabled={globalPipelineRunning}
                        title={globalPipelineRunning ? "Another pipeline is already running. Wait for it to complete." : ""}
                        onClick={() => {
                          if (globalPipelineRunning) return;
                          onRunPipeline(doc);
                        }}
                      >
                        {globalPipelineRunning ? (
                          "Pipeline Busy"
                        ) : (
                          <>
                            Run Pipeline
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: 5 }}>
                              <polygon points="5 3 19 12 5 21 5 3"/>
                            </svg>
                          </>
                        )}
                      </button>
                    </div>
                  ) : (
                    /* Fully done → Open Pipeline only */
                    <button
                      className="primary-button lib-card-open"
                      onClick={() => onSelectDocument(doc)}
                    >
                      Open Pipeline
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: 6 }}>
                        <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                      </svg>
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
