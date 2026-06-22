/**
 * DocumentIntelligenceWorkbench — Orchestrator
 *
 * Manages all state, API calls, and polling. Renders one of four child pages:
 *   1. DocumentLibraryPage  — default landing, upload + card grid
 *   2. DocumentPipelinePage — per-document sequential pipeline stepper
 *   3. RuleReviewPage       — location-aware rule candidate review
 *   4. HandoffPage          — exports + API contract
 *
 * Navigation is state-driven (no URLs needed). "Back to Library" always works.
 *
 * Pipeline state persistence:
 *   sessionStorage key "di_pipeline_running" stores the documentId of any
 *   actively-running pipeline. On remount we check this key and restore the
 *   busy + polling state so navigating away and back is seamless.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { documentApi, candidateApi } from "../../lib/api";
import DocumentLibraryPage from "./DocumentLibraryPage";
import DocumentPipelinePage from "./DocumentPipelinePage";
import RuleReviewPage from "./RuleReviewPage";
import HandoffPage from "./HandoffPage";

// ── View names ────────────────────────────────────────────────────────────
const VIEW = {
  LIBRARY: "library",
  PIPELINE: "pipeline",
  REVIEW: "review",
  HANDOFF: "handoff",
};

// sessionStorage key tracking which documentId is actively processing
const SS_KEY = "di_pipeline_running";

// ── Helpers ───────────────────────────────────────────────────────────────
function readError(err) {
  if (!err) return "Request failed.";
  try {
    const parsed = JSON.parse(err.message);
    return parsed.detail?.message || parsed.message || err.message;
  } catch {
    return err.message || "Request failed.";
  }
}

function exportsFromSummary(summary) {
  if (!summary?.exports) return {};
  return summary.exports.reduce((acc, item) => {
    acc[item.name] = { path: item.path, exists: item.exists };
    return acc;
  }, {});
}

/** Returns true if the document's pipeline is incomplete (still has work to do). */
function pipelineIsIncomplete(summary) {
  const p = summary?.pipeline || {};
  return !(p.normalized || p.ready_for_review);
}

// ── Workbench ─────────────────────────────────────────────────────────────
export default function DocumentIntelligenceWorkbench({ backendOnline }) {
  // ── Documents list ──────────────────────────────────────────────────────
  const [documents, setDocuments] = useState([]);
  const [summaries, setSummaries] = useState({}); // keyed by document_id

  // ── Selected document state ────────────────────────────────────────────
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [exportsMap, setExportsMap] = useState({});
  const [qualityReport, setQualityReport] = useState(null);

  // ── UI state ───────────────────────────────────────────────────────────
  const [currentView, setCurrentView] = useState(VIEW.LIBRARY);
  const [busyStage, setBusyStage] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  // ── Polling ───────────────────────────────────────────────────────────
  const pollRef = useRef(null);

  // ── Derived ───────────────────────────────────────────────────────────
  const selectedDocument = useMemo(
    () => documents.find(d => d.document_id === selectedDocumentId) || null,
    [documents, selectedDocumentId]
  );
  const selectedSummary = selectedDocumentId ? summaries[selectedDocumentId] : null;

  // ── API fetchers ──────────────────────────────────────────────────────

  const fetchDocuments = useCallback(async () => {
    if (!backendOnline) { setDocuments([]); return; }
    const list = await documentApi.list();
    setDocuments(list || []);
  }, [backendOnline]);

  const fetchDocumentDetails = useCallback(async (documentId) => {
    if (!documentId || !backendOnline) {
      setChunks([]);
      setCandidates([]);
      setExportsMap({});
      setQualityReport(null);
      return null;
    }
    const [chunkPayload, candidatePayload, summaryPayload] = await Promise.allSettled([
      documentApi.chunks(documentId),
      documentApi.candidates(documentId),
      documentApi.summary(documentId),
    ]);
    setChunks(chunkPayload.status === "fulfilled" ? chunkPayload.value?.chunks || [] : []);
    setCandidates(candidatePayload.status === "fulfilled" ? candidatePayload.value?.rule_candidates || [] : []);
    let summary = null;
    if (summaryPayload.status === "fulfilled") {
      summary = summaryPayload.value;
      setSummaries(prev => ({ ...prev, [documentId]: summary }));
      setQualityReport(summary?.quality?.report || null);
      setExportsMap(exportsFromSummary(summary));
    }
    return summary;
  }, [backendOnline]);

  // ── Start / stop polling ──────────────────────────────────────────────

  const startPolling = useCallback((documentId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        await fetchDocuments();
        const summary = await fetchDocumentDetails(documentId);
        // Auto-stop poll when pipeline reaches a terminal state
        if (summary && !pipelineIsIncomplete(summary)) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setBusyStage("");
          sessionStorage.removeItem(SS_KEY);
        }
      } catch { /* ignore poll errors */ }
    }, 3500);
  }, [fetchDocuments, fetchDocumentDetails]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // ── Initial load ──────────────────────────────────────────────────────
  useEffect(() => {
    fetchDocuments().catch(err => setError(readError(err)));
    return () => stopPolling();
  }, [backendOnline]);

  // ── Load details when selected document changes ───────────────────────
  useEffect(() => {
    if (!selectedDocumentId) return;

    fetchDocumentDetails(selectedDocumentId)
      .then(summary => {
        // ── Restore pipeline busy state after navigation ──
        const runningId = sessionStorage.getItem(SS_KEY);
        if (runningId === selectedDocumentId) {
          // The pipeline was running before we navigated away.
          // Check if it's actually still incomplete.
          if (summary && pipelineIsIncomplete(summary)) {
            // Still running — restore busy state and resume polling.
            setBusyStage("Run Full Pipeline");
            startPolling(selectedDocumentId);
          } else {
            // Finished while we were away — clean up.
            sessionStorage.removeItem(SS_KEY);
            setBusyStage("");
          }
        }
      })
      .catch(err => setError(readError(err)));
  }, [selectedDocumentId, backendOnline]);

  // ── Navigation ────────────────────────────────────────────────────────

  const openDocument = useCallback((doc) => {
    setSelectedDocumentId(doc.document_id);
    setSelectedCandidate(null);
    setError("");
    setNotice("");
    setCurrentView(VIEW.PIPELINE);
  }, []);

  const returnToLibrary = useCallback(() => {
    // Don't clear busyStage — let it persist so navigating back shows the running state.
    setSelectedDocumentId(null);
    setSelectedCandidate(null);
    setChunks([]);
    setCandidates([]);
    setExportsMap({});
    setQualityReport(null);
    setError("");
    setNotice("");
    setCurrentView(VIEW.LIBRARY);
    // Keep polling going in the background while in library view
    // (it auto-stops when pipeline completes)
  }, []);

  const navigateTo = useCallback((view) => {
    setError("");
    setNotice("");
    setCurrentView(view);
  }, []);

  // ── Pipeline runner ───────────────────────────────────────────────────

  const runStage = useCallback(async (stageKey, runnerFn, targetDocumentId) => {
    const docId = targetDocumentId || selectedDocumentId;
    if (!docId || !runnerFn) return;

    // ── Concurrency guard: prevent starting if another pipeline is running ──
    const alreadyRunningId = sessionStorage.getItem(SS_KEY);
    if (alreadyRunningId && alreadyRunningId !== docId) {
      setError(
        `Another pipeline is already processing (${alreadyRunningId}). ` +
        `Please wait for it to complete before starting a new one.`
      );
      return;
    }
    if (busyStage) {
      setError("This pipeline is already running. Please wait for it to complete.");
      return;
    }

    // Mark as running
    setBusyStage(stageKey);
    sessionStorage.setItem(SS_KEY, docId);
    setError("");
    setNotice("");

    // Start polling immediately so each stage shows live progress
    startPolling(docId);

    try {
      await runnerFn(docId);
      setNotice("Pipeline stage completed successfully.");
      await fetchDocuments();
      await fetchDocumentDetails(docId);
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusyStage("");
      sessionStorage.removeItem(SS_KEY);
      stopPolling();
      // One final refresh to sync the state
      fetchDocuments().catch(() => {});
      fetchDocumentDetails(docId).catch(() => {});
    }
  }, [selectedDocumentId, busyStage, fetchDocuments, fetchDocumentDetails, startPolling, stopPolling]);

  const startPipeline = useCallback((docId) => {
    runStage("Run Full Pipeline", documentApi.runPipeline, docId);
  }, [runStage]);

  // Called from Library: upload then auto-run pipeline
  const handleUploadAndRun = useCallback(async (doc) => {
    openDocument(doc);
    // Small delay so the pipeline view renders first, then kick off
    setTimeout(() => {
      runStage("Run Full Pipeline", documentApi.runPipeline, doc.document_id);
    }, 300);
  }, [openDocument, runStage]);

  // ── Review actions ────────────────────────────────────────────────────

  const updateReview = useCallback(async (candidateId, status, extra = {}) => {
    setError("");
    setNotice("");
    try {
      await candidateApi.review(candidateId, status, {
        tier: extra.tier || null,
        auto_approved: extra.auto_approved || null,
        rejection_reason: extra.rejection_reason || null,
        notes: extra.notes || "",
      });
      setCandidates(prev => {
        const updated = prev.map(c =>
          c.candidate_id === candidateId
            ? {
                ...c,
                review_status: status,
                metadata_json: {
                  ...(c.metadata_json || {}),
                  ...(extra.rejection_reason ? { rejection_reason: extra.rejection_reason } : {}),
                  ...(extra.tier ? { review_tier: extra.tier } : {}),
                },
              }
            : c
        );
        setSelectedCandidate(sel =>
          sel?.candidate_id === candidateId
            ? { ...sel, review_status: status }
            : sel
        );
        return updated;
      });
      setNotice("Review status updated.");
    } catch (err) {
      setError(readError(err));
    }
  }, [selectedDocumentId]);

  const refreshCandidates = useCallback(async () => {
    if (!selectedDocumentId || !backendOnline) return;
    try {
      const payload = await documentApi.candidates(selectedDocumentId);
      const freshCandidates = payload?.rule_candidates || [];
      setCandidates(freshCandidates);
      // Also update selected candidate if still open
      setSelectedCandidate(sel => {
        if (!sel) return sel;
        return freshCandidates.find(c => c.candidate_id === sel.candidate_id) || sel;
      });
    } catch { /* silently ignore refresh errors */ }
  }, [selectedDocumentId, backendOnline]);

  const runPostReviewPipeline = useCallback(() => {
    setNotice(
      "🚧 Coming soon — Post-review pipeline promotion will be handled by the next backend phase. " +
      "Your approved candidates are stored and available via the API for the downstream service."
    );
  }, []);

  // ── Breadcrumb / nav bar ──────────────────────────────────────────────
  const isInDocument = currentView !== VIEW.LIBRARY;
  const docName =
    selectedDocument?.display_name ||
    selectedDocument?.original_filename ||
    selectedDocument?.filename ||
    selectedDocumentId || "";

  // Derive "any pipeline currently running" for library concurrency warning
  const globalPipelineRunning = !!sessionStorage.getItem(SS_KEY);

  return (
    <div className="diw-root">
      {/* Top breadcrumb + tab nav */}
      <div className="diw-topnav">
        <div className="diw-breadcrumb">
          <button
            className={`diw-breadcrumb-item ${currentView === VIEW.LIBRARY ? "active" : "link-button"}`}
            onClick={returnToLibrary}
          >
            Document Library
          </button>
          {isInDocument && (
            <>
              <span className="diw-breadcrumb-sep">›</span>
              <span className="diw-breadcrumb-item diw-breadcrumb-doc" title={docName}>
                {docName.length > 40 ? docName.slice(0, 40) + "…" : docName}
              </span>
              {busyStage && (
                <span className="diw-breadcrumb-running">
                  <span className="pip-running-dot" style={{ width: 7, height: 7 }} />
                  Processing
                </span>
              )}
            </>
          )}
        </div>

        {isInDocument && (
          <div className="diw-tabs">
            {[
              { view: VIEW.PIPELINE, label: "Pipeline" },
              { view: VIEW.REVIEW, label: `Rule Review${candidates.length ? ` (${candidates.length})` : ""}` },
              { view: VIEW.HANDOFF, label: "Handoff" },
            ].map(({ view, label }) => (
              <button
                key={view}
                className={`diw-tab ${currentView === view ? "active" : ""}`}
                onClick={() => navigateTo(view)}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {isInDocument && (
          <button className="secondary-button diw-back-btn" onClick={returnToLibrary}>
            ← Library
          </button>
        )}
      </div>

      {/* Global alerts */}
      {error && (
        <div className="di-alert error diw-alert" onClick={() => setError("")}>
          {error} <span className="diw-alert-dismiss">×</span>
        </div>
      )}
      {notice && !error && (
        <div className="di-alert success diw-alert" onClick={() => setNotice("")}>
          {notice} <span className="diw-alert-dismiss">×</span>
        </div>
      )}

      {/* Page content */}
      <div className="diw-content">
        {currentView === VIEW.LIBRARY && (
          <DocumentLibraryPage
            backendOnline={backendOnline}
            documents={documents}
            summaries={summaries}
            globalPipelineRunning={globalPipelineRunning}
            globalPipelineDocId={sessionStorage.getItem(SS_KEY)}
            onSelectDocument={openDocument}
            onRunPipeline={(doc) => {
              openDocument(doc);
              setTimeout(() => startPipeline(doc.document_id), 300);
            }}
            onUploaded={(doc) => {
              fetchDocuments().catch(() => {});
              handleUploadAndRun(doc);
            }}
          />
        )}

        {currentView === VIEW.PIPELINE && selectedDocument && (
          <DocumentPipelinePage
            document={selectedDocument}
            summary={selectedSummary}
            busyStage={busyStage}
            backendOnline={backendOnline}
            onRunStage={runStage}
            onStartPipeline={() => startPipeline(selectedDocumentId)}
            onGoToReview={() => navigateTo(VIEW.REVIEW)}
          />
        )}

        {currentView === VIEW.REVIEW && selectedDocument && (
          <RuleReviewPage
            document={selectedDocument}
            candidates={candidates}
            selectedCandidate={selectedCandidate}
            onSelectCandidate={setSelectedCandidate}
            onUpdateReview={updateReview}
            backendOnline={backendOnline}
            onRunPostReview={runPostReviewPipeline}
            onRefreshCandidates={refreshCandidates}
          />
        )}

        {currentView === VIEW.HANDOFF && selectedDocument && (
          <HandoffPage
            document={selectedDocument}
            summary={selectedSummary}
            candidates={candidates}
            exportsMap={exportsMap}
            qualityReport={qualityReport}
          />
        )}
      </div>
    </div>
  );
}
