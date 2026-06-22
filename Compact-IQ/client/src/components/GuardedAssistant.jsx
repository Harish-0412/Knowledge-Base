import React, { useState, useEffect, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

// ── Mode & Intent display metadata ──────────────────────────────────────────

const MODE_META = {
  answered_with_document_evidence: { label: "Document Evidence",    color: "#16a34a", bg: "#f0fdf4", border: "#86efac" },
  answered_general_concept:        { label: "General Concept",      color: "#0369a1", bg: "#f0f9ff", border: "#7dd3fc" },
  blocked_out_of_scope:            { label: "Out of Scope",         color: "#b91c1c", bg: "#fef2f2", border: "#fca5a5" },
  blocked_unsafe:                  { label: "Blocked — Unsafe",     color: "#b91c1c", bg: "#fef2f2", border: "#fca5a5" },
  capability_missing:              { label: "Capability Missing",   color: "#92400e", bg: "#fffbeb", border: "#fcd34d" },
  insufficient_evidence:           { label: "Insufficient Evidence",color: "#7c3aed", bg: "#faf5ff", border: "#c4b5fd" },
  needs_human_review:              { label: "Needs Human Review",   color: "#b45309", bg: "#fffbeb", border: "#fbbf24" },
  error:                           { label: "Error",                color: "#6b7280", bg: "#f9fafb", border: "#d1d5db" },
};

const INTENT_LABEL = {
  normalized_rule_lookup: "Rule Lookup",
  rule_candidate_lookup: "Candidate Lookup",
  review_status_lookup: "Review Status",
  chunk_evidence_lookup: "Evidence Lookup",
  source_trace: "Source Trace",
  remediation_from_document: "Remediation",
  unsupported_config_lookup: "Unsupported Config",
  document_summary: "Document Summary",
  document_metadata_lookup: "Document Metadata",
  general_compatibility_concept: "General Concept",
  capability_question: "Capability Question",
  handoff_status: "Handoff Status",
  requires_kg: "Requires KG",
  requires_kb: "Requires KB",
  requires_inventory: "Requires Inventory",
  requires_compliance_scan: "Requires Compliance Scan",
  out_of_scope: "Out of Scope",
  known_issue_lookup: "Known Issue",
  compatibility_explanation: "Compatibility",
};

const SAMPLE_QUESTIONS = [
  "What rules were extracted from this document?",
  "Show evidence for TPM Firmware 7.2.4.1",
  "What unsupported configurations were found?",
  "Which candidates are pending review?",
  "What is a minimum version rule?",
  "Which devices violate COMP-006?",
  "Tell me a joke",
];

// ── Sub-components ─────────────────────────────────────────────────────────

function GuardrailBadge({ mode }) {
  const meta = MODE_META[mode] || MODE_META.error;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700,
      color: meta.color, background: meta.bg,
      border: `1px solid ${meta.border}`, letterSpacing: "0.03em"
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%",
        background: meta.color, display: "inline-block"
      }} />
      {meta.label}
    </span>
  );
}

function IntentBadge({ intent }) {
  const label = INTENT_LABEL[intent] || intent;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 8px", borderRadius: 20, fontSize: 10.5, fontWeight: 600,
      color: "#374151", background: "#f3f4f6",
      border: "1px solid #e5e7eb", letterSpacing: "0.02em"
    }}>
      ◈ {label}
    </span>
  );
}

function MarkdownText({ text }) {
  if (!text) return null;
  return (
    <>
      {text.split("\n").map((line, i) => {
        if (!line.trim()) return <div key={i} style={{ height: 4 }} />;
        if (/^>\s/.test(line)) {
          return (
            <div key={i} style={{
              borderLeft: "3px solid #fbbf24", paddingLeft: 10,
              color: "#78350f", fontStyle: "italic", marginBottom: 4, fontSize: 12.5
            }}>
              {line.slice(2)}
            </div>
          );
        }
        if (line.startsWith("- ") || line.startsWith("* ")) {
          const content = line.slice(2);
          const parts = content.split(/\*\*(.*?)\*\*/g);
          return (
            <div key={i} style={{ display: "flex", gap: 6, marginBottom: 3, fontSize: 13 }}>
              <span style={{ color: "#6366f1", flexShrink: 0 }}>•</span>
              <span>
                {parts.map((p, j) => j % 2 === 1
                  ? <strong key={j} style={{ color: "#1e40af" }}>{p}</strong>
                  : p
                )}
              </span>
            </div>
          );
        }
        if (line.includes("**")) {
          const parts = line.split(/\*\*(.*?)\*\*/g);
          return (
            <p key={i} style={{ margin: "0 0 6px", fontSize: 13 }}>
              {parts.map((p, j) => j % 2 === 1
                ? <strong key={j} style={{ color: "#1e40af" }}>{p}</strong>
                : p
              )}
            </p>
          );
        }
        return <p key={i} style={{ margin: "0 0 6px", fontSize: 13 }}>{line}</p>;
      })}
    </>
  );
}

function EvidenceCard({ ev }) {
  return (
    <div style={{
      background: "#f8fafc", border: "1px solid #e2e8f0",
      borderRadius: 8, padding: "8px 11px", fontSize: 11.5
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontWeight: 700, color: "#1e40af" }}>
          {ev.title || ev.source_id || "Evidence"}
        </span>
        <div style={{ display: "flex", gap: 5 }}>
          {ev.review_status && (
            <span style={{
              padding: "1px 7px", borderRadius: 10, fontSize: 10, fontWeight: 600,
              background: ev.review_status === "approved" ? "#f0fdf4" : "#fef3c7",
              color: ev.review_status === "approved" ? "#15803d" : "#92400e",
              border: `1px solid ${ev.review_status === "approved" ? "#86efac" : "#fcd34d"}`
            }}>
              {ev.review_status}
            </span>
          )}
          <span style={{
            padding: "1px 6px", borderRadius: 10, fontSize: 10,
            background: "#f1f5f9", color: "#64748b", border: "1px solid #e2e8f0"
          }}>
            {(ev.source_type || "").replace(/_/g, " ")}
          </span>
        </div>
      </div>
      {ev.source_excerpt && (
        <div style={{
          fontStyle: "italic", color: "#475569",
          borderLeft: "2px solid #cbd5e1", paddingLeft: 8, marginTop: 4, fontSize: 11
        }}>
          &ldquo;{ev.source_excerpt.slice(0, 240)}{ev.source_excerpt.length > 240 ? "…" : ""}&rdquo;
        </div>
      )}
      <div style={{ display: "flex", gap: 10, marginTop: 5, color: "#94a3b8", fontSize: 10.5 }}>
        {ev.source_document_id && <span>Doc: {ev.source_document_id}</span>}
        {ev.source_page && <span>Page {ev.source_page}</span>}
        {ev.confidence != null && <span>Conf: {(ev.confidence * 100).toFixed(0)}%</span>}
      </div>
    </div>
  );
}

function GuardedMessageBubble({ msg }) {
  const [traceOpen, setTraceOpen] = useState(false);

  if (msg.sender === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
        <div style={{
          maxWidth: "70%", background: "#1e40af", color: "#fff",
          borderRadius: "18px 18px 4px 18px", padding: "10px 14px",
          fontSize: 13, lineHeight: 1.5
        }}>
          {msg.content}
          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", marginTop: 4, textAlign: "right" }}>
            {msg.timestamp}
          </div>
        </div>
      </div>
    );
  }

  const { answer, mode, intent, allowed, evidence_used, limitations,
          suggested_next_actions, guardrail_trace, timestamp } = msg;
  const modeMeta = MODE_META[mode] || MODE_META.error;
  const isBlocked = !allowed;

  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 20, alignItems: "flex-start" }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: "50%",
        background: isBlocked ? "#fef2f2" : "#eff6ff",
        border: `1.5px solid ${modeMeta.border}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0, marginTop: 2
      }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke={modeMeta.color} strokeWidth="2.5">
          <rect x="3" y="11" width="18" height="10" rx="2"/>
          <circle cx="12" cy="5" r="2"/><path d="M12 7v4"/>
        </svg>
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>CompatIQ Assistant</span>
          <GuardrailBadge mode={mode} />
          {intent && intent !== "out_of_scope" && <IntentBadge intent={intent} />}
          <span style={{ fontSize: 11, color: "#94a3b8", marginLeft: "auto" }}>{timestamp}</span>
        </div>

        {/* Answer bubble */}
        <div style={{
          background: isBlocked ? "#fef2f2" : "#fff",
          border: `1px solid ${isBlocked ? "#fca5a5" : "#e2e8f0"}`,
          borderLeft: `3px solid ${modeMeta.color}`,
          borderRadius: "0 10px 10px 10px",
          padding: "12px 14px", lineHeight: 1.65, color: "#1e293b"
        }}>
          <MarkdownText text={answer} />
        </div>

        {/* Evidence */}
        {evidence_used && evidence_used.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <div style={{
              fontSize: 10.5, fontWeight: 700, color: "#475569",
              textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6
            }}>
              📄 Evidence Used ({evidence_used.length})
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {evidence_used.slice(0, 4).map((ev, i) => <EvidenceCard key={i} ev={ev} />)}
            </div>
          </div>
        )}

        {/* Limitations */}
        {limitations && limitations.length > 0 && (
          <div style={{
            marginTop: 10, padding: "8px 12px",
            background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 8
          }}>
            <div style={{ fontWeight: 700, color: "#92400e", marginBottom: 4, fontSize: 11 }}>
              ⚠️ Limitations
            </div>
            {limitations.slice(0, 3).map((lim, i) => (
              <div key={i} style={{ color: "#78350f", fontSize: 11.5, marginBottom: 2 }}>• {lim}</div>
            ))}
          </div>
        )}

        {/* Suggested next actions */}
        {suggested_next_actions && suggested_next_actions.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <div style={{
              fontSize: 10.5, fontWeight: 700, color: "#475569",
              textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 5
            }}>Next Steps</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
              {suggested_next_actions.map((a, i) => (
                <span key={i} style={{
                  padding: "3px 10px", borderRadius: 20, fontSize: 11,
                  background: "#f1f5f9", color: "#374151", border: "1px solid #e2e8f0"
                }}>→ {a}</span>
              ))}
            </div>
          </div>
        )}

        {/* Guardrail trace */}
        {guardrail_trace && Object.keys(guardrail_trace).length > 0 && (
          <div style={{ marginTop: 10 }}>
            <button
              onClick={() => setTraceOpen(v => !v)}
              style={{
                background: "none", border: "1px solid #e2e8f0", borderRadius: 6,
                padding: "3px 10px", fontSize: 10.5, color: "#64748b",
                cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 5
              }}
            >
              <span style={{ fontSize: 9 }}>{traceOpen ? "▲" : "▼"}</span>
              Guardrail Trace {traceOpen ? "(hide)" : "(debug)"}
            </button>
            {traceOpen && (
              <div style={{
                marginTop: 6, background: "#0f172a", color: "#94a3b8",
                borderRadius: 8, padding: "10px 14px", fontSize: 11,
                fontFamily: "monospace", lineHeight: 1.6, overflow: "auto", maxHeight: 260
              }}>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(guardrail_trace, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function GuardedAssistant({
  backendOnline, analysisRun, devicesCount, violationsCount, rulesApprovedCount
}) {
  const [messages, setMessages] = useState([]);
  const [typing, setTyping] = useState(false);
  const [inputText, setInputText] = useState("");
  const [includeTrace, setIncludeTrace] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const handleSend = (text) => {
    if (!text.trim() || !backendOnline) return;
    const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages(prev => [...prev, { sender: "user", content: text, timestamp: ts }]);
    setInputText("");
    setTyping(true);

    fetch(`${API_BASE}/api/assistant/guarded-query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text, include_guardrail_trace: includeTrace }),
    })
      .then(res => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
      .then(data => {
        setTyping(false);
        const ts2 = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setMessages(prev => [...prev, { sender: "assistant", timestamp: ts2, ...data }]);
      })
      .catch(err => {
        console.warn("Guardrail API error:", err);
        setTyping(false);
        const ts2 = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setMessages(prev => [...prev, {
          sender: "assistant", timestamp: ts2,
          answer: "The guardrail assistant service is not reachable. Please check the FastAPI backend.",
          mode: "error", intent: "error", allowed: false,
          evidence_used: [], limitations: ["Backend not reachable"],
          suggested_next_actions: ["Start the backend: uvicorn app.main:app --reload --port 8000"],
          guardrail_trace: {},
        }]);
      });
  };

  // PanelHeader replication since this is a separate file
  const PanelHeader = ({ title, meta, children }) => (
    <div className="panel-header">
      <div>
        <h2>{title}</h2>
        {meta && <p>{meta}</p>}
      </div>
      {children && <div className="panel-actions">{children}</div>}
    </div>
  );

  return (
    <div className="split-layout">
      {/* ── Main chat panel ── */}
      <section className="panel chat-panel" style={{
        height: "calc(100vh - 120px)", display: "flex", flexDirection: "column"
      }}>
        <PanelHeader
          title="CompatIQ Guarded Assistant"
          meta={backendOnline ? "Guardrail pipeline active — Document Intelligence mode" : "Offline"}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <label style={{
              display: "flex", alignItems: "center", gap: 5,
              fontSize: 11, color: "var(--muted)", cursor: "pointer"
            }}>
              <input type="checkbox" checked={includeTrace}
                onChange={e => setIncludeTrace(e.target.checked)} />
              Debug Trace
            </label>
            <span className={`badge ${backendOnline ? "success" : "neutral"}`}
              style={{ height: 24, fontSize: 10.5 }}>
              <span className={`status-dot ${backendOnline ? "success-dot" : "neutral-dot"}`}
                style={{ width: 6, height: 6, marginRight: 6 }} />
              {backendOnline ? "Guardrails Active" : "Offline"}
            </span>
          </div>
        </PanelHeader>

        {!backendOnline && (
          <div style={{
            margin: "16px", padding: "16px",
            background: "#fffbeb", border: "1px dashed #fcd34d",
            borderRadius: 8, textAlign: "center", color: "#b45309"
          }}>
            <p style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>⚠️ Backend Offline</p>
            <p style={{ margin: "8px 0 0", fontSize: 12.5 }}>
              Start the FastAPI backend to enable the guardrail assistant pipeline.
            </p>
          </div>
        )}

        {/* Messages area */}
        <div className="chat-history-scrollable" style={{
          flex: 1, overflowY: "auto", padding: "16px 20px",
          opacity: !backendOnline ? 0.7 : 1
        }}>
          {messages.length === 0 ? (
            <div style={{ maxWidth: 680, margin: "0 auto" }}>
              {/* Hero */}
              <div style={{ textAlign: "center", marginBottom: 28 }}>
                <div style={{
                  width: 52, height: 52, borderRadius: "50%",
                  background: "linear-gradient(135deg, #1e40af, #7c3aed)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  margin: "0 auto 12px"
                }}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                    stroke="white" strokeWidth="2.5">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  </svg>
                </div>
                <h3 style={{ margin: "0 0 6px", fontSize: 18, fontWeight: 800, color: "#0f172a" }}>
                  CompatIQ Guarded Assistant
                </h3>
                <p style={{ margin: 0, color: "#64748b", fontSize: 13, lineHeight: 1.6 }}>
                  Production-grade guardrail pipeline. Every question is scope-checked,
                  intent-classified, evidence-retrieved, and output-validated.
                </p>
              </div>

              {/* Capability pills */}
              <div style={{ display: "flex", gap: 8, justifyContent: "center",
                flexWrap: "wrap", marginBottom: 24 }}>
                {[
                  ["✓ Document Intelligence", "#15803d", "#f0fdf4", "#86efac"],
                  ["✓ Rule Candidates",       "#15803d", "#f0fdf4", "#86efac"],
                  ["✓ Review Status",         "#15803d", "#f0fdf4", "#86efac"],
                  ["◌ Inventory",             "#94a3b8", "#f8fafc", "#e2e8f0"],
                  ["◌ Knowledge Graph",       "#94a3b8", "#f8fafc", "#e2e8f0"],
                  ["◌ Compliance Scan",       "#94a3b8", "#f8fafc", "#e2e8f0"],
                ].map(([label, color, bg, border]) => (
                  <span key={label} style={{
                    padding: "4px 12px", borderRadius: 20, fontSize: 11, fontWeight: 700,
                    color, background: bg, border: `1px solid ${border}`
                  }}>{label}</span>
                ))}
              </div>

              {/* Sample questions */}
              <div style={{ marginBottom: 12 }}>
                <div style={{
                  fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                  color: "#94a3b8", marginBottom: 10, letterSpacing: "0.06em", textAlign: "center"
                }}>
                  Sample Questions — last 2 demonstrate guardrails
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                  {SAMPLE_QUESTIONS.map((q, i) => {
                    const isDemo = i >= 5;
                    return (
                      <button
                        key={q}
                        onClick={() => handleSend(q)}
                        disabled={!backendOnline || typing}
                        style={{
                          textAlign: "left", padding: "10px 14px",
                          background: isDemo ? "#fef2f2" : "#f8fafc",
                          border: `1px solid ${isDemo ? "#fca5a5" : "#e2e8f0"}`,
                          borderRadius: 10, fontSize: 12.5, cursor: "pointer",
                          color: isDemo ? "#b91c1c" : "#1e293b",
                          fontWeight: 500,
                          display: "flex", justifyContent: "space-between", alignItems: "center",
                          opacity: (!backendOnline || typing) ? 0.5 : 1,
                        }}
                      >
                        <span>{q}</span>
                        <span style={{ fontSize: 10, color: isDemo ? "#ef4444" : "#94a3b8" }}>
                          {isDemo ? (i === 5 ? "→ capability_missing" : "→ blocked") : "→ try"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            messages.map((m, i) => <GuardedMessageBubble key={i} msg={m} />)
          )}

          {typing && (
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 16 }}>
              <div style={{
                width: 32, height: 32, borderRadius: "50%",
                background: "#eff6ff", border: "1.5px solid #93c5fd",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke="#1e40af" strokeWidth="2.5">
                  <rect x="3" y="11" width="18" height="10" rx="2"/>
                  <circle cx="12" cy="5" r="2"/><path d="M12 7v4"/>
                </svg>
              </div>
              <div style={{
                background: "#f8fafc", border: "1px solid #e2e8f0",
                borderRadius: "0 10px 10px 10px", padding: "12px 16px"
              }}>
                <div style={{ fontSize: 11, color: "#64748b", marginBottom: 6 }}>
                  Running guardrail pipeline…
                </div>
                <div className="typing-indicator-dots">
                  <span className="typing-indicator-dot" />
                  <span className="typing-indicator-dot" />
                  <span className="typing-indicator-dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input footer */}
        <div style={{
          borderTop: "1px solid var(--border)", padding: "12px 20px",
          background: "var(--surface-2)"
        }}>
          <div style={{ display: "flex", gap: 8, marginBottom: messages.length > 0 ? 8 : 0 }}>
            <div className="message-input-container" style={{ flex: 1, margin: 0 }}>
              <input
                placeholder={backendOnline
                  ? "Ask about rules, documents, evidence, or review status…"
                  : "Backend offline — start FastAPI to query"}
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSend(inputText)}
                disabled={typing || !backendOnline}
                style={{ opacity: !backendOnline ? 0.6 : 1 }}
              />
            </div>
            <button
              className="primary-button"
              onClick={() => handleSend(inputText)}
              disabled={typing || !inputText.trim() || !backendOnline}
              style={{ display: "flex", alignItems: "center", gap: 6, padding: "0 16px" }}
            >
              Send
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
          {messages.length > 0 && (
            <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
              {SAMPLE_QUESTIONS.slice(0, 4).map(q => (
                <button key={q} onClick={() => handleSend(q)}
                  disabled={typing || !backendOnline}
                  style={{
                    padding: "3px 9px", background: "var(--surface)",
                    border: "1px solid var(--border)", borderRadius: 6,
                    fontSize: 11, color: "var(--secondary)", cursor: "pointer"
                  }}>
                  {q.length > 36 ? q.slice(0, 36) + "…" : q}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── Right sidebar ── */}
      <aside className="panel detail-panel" style={{
        position: "sticky", top: 88,
        maxHeight: "calc(100vh - 110px)", overflowY: "auto"
      }}>
        <div className="drawer-sections">

          {/* Guardrail pipeline status */}
          <div className="drawer-section" style={{ background: "#0f172a", color: "#e2e8f0" }}>
            <div className="drawer-section-title" style={{
              background: "rgba(255,255,255,0.04)", color: "#94a3b8",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
              padding: "10px 16px", fontSize: 10, fontWeight: 800,
              textTransform: "uppercase", letterSpacing: "0.07em"
            }}>
              Guardrail Pipeline
            </div>
            <div className="drawer-section-body" style={{ padding: "12px 16px" }}>
              {[
                ["🔒 Scope Check",        true,  "Domain filter + injection detection"],
                ["🎯 Intent Classifier",  true,  "19-intent deterministic rules"],
                ["📦 Retrieval Router",   true,  "Evidence from Document Intelligence"],
                ["✅ Output Validator",   true,  "Hallucination + OOS detection"],
                ["📝 Audit Logger",       true,  "JSONL at storage/guardrail_audit.jsonl"],
                ["🕸️ KG Traversal",       false, "Knowledge Graph — not connected"],
                ["📦 Inventory",          false, "Device inventory — not connected"],
                ["🔍 Compliance Scan",    false, "Compliance scan — not connected"],
              ].map(([label, active, tip]) => (
                <div key={label} title={tip} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "5px 0", borderBottom: "1px solid rgba(255,255,255,0.06)"
                }}>
                  <span style={{ fontSize: 11.5, color: active ? "#e2e8f0" : "#475569" }}>
                    {label}
                  </span>
                  <span style={{
                    fontSize: 9.5, fontWeight: 700, padding: "2px 7px", borderRadius: 10,
                    background: active ? "rgba(34,197,94,0.15)" : "rgba(255,255,255,0.04)",
                    color: active ? "#4ade80" : "#64748b",
                    border: `1px solid ${active ? "rgba(34,197,94,0.3)" : "rgba(255,255,255,0.06)"}`
                  }}>
                    {active ? "Active" : "Stub"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Current mode */}
          <div className="drawer-section">
            <div className="drawer-section-title">Current Mode</div>
            <div className="drawer-section-body" style={{ padding: "12px 16px" }}>
              <div style={{
                background: "#eff6ff", border: "1px solid #93c5fd",
                borderRadius: 8, padding: "10px 12px"
              }}>
                <div style={{ fontWeight: 700, fontSize: 12, color: "#1e40af", marginBottom: 4 }}>
                  Document Intelligence Only
                </div>
                <div style={{ fontSize: 11.5, color: "#3b82f6", lineHeight: 1.5 }}>
                  Answers from uploaded documents, extracted chunks, and rule candidates.
                  KB/KG modules plug in when connected — no code changes needed.
                </div>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="drawer-section">
            <div className="drawer-section-title">Environment</div>
            <div className="drawer-section-body" style={{ padding: "12px 16px" }}>
              {[
                ["Approved Rules", rulesApprovedCount, "#15803d"],
                ["Devices Indexed", devicesCount, "#1e40af"],
                ["Violations Found", violationsCount, "#b91c1c"],
              ].map(([label, val, col]) => (
                <div key={label} className="assistant-info-stat-row">
                  <span className="assistant-info-stat-label">{label}</span>
                  <span className="assistant-info-stat-val" style={{ color: col }}>
                    {backendOnline ? val : "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </aside>
    </div>
  );
}
