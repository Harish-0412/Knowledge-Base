import React, { useMemo, useRef, useState } from "react";
import { rulebookEntries, rulebookFamilies, rulebookStats, severityOrder } from "../data/compatibilityRulebook";
import { API_BASE } from "../lib/api";

// ── helpers ─────────────────────────────────────────────────────────────────

function searchableText(entry) {
  return [
    entry.title,
    entry.family,
    entry.versions,
    entry.status,
    entry.summary,
    entry.description || "",
    ...(entry.requirements || []),
    ...(entry.knownIssues || []),
    ...(entry.tags || []),
    ...(entry.checks || []).flatMap(c => [c.label, c.command]),
    ...(entry.affectedComponents || []),
  ].join(" ").toLowerCase();
}

function highlight(text, query) {
  const terms = query.trim().split(/\s+/).filter(t => t.length > 2);
  if (!terms.length) return text;
  const escaped = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "ig");
  return String(text).split(pattern).map((part, i) =>
    terms.some(t => t.toLowerCase() === part.toLowerCase())
      ? <mark key={`${part}-${i}`}>{part}</mark>
      : part
  );
}

const SEVERITY_META = {
  Critical: { cls: "sev-critical", color: "#dc2626" },
  High:     { cls: "sev-high",     color: "#ea580c" },
  Medium:   { cls: "sev-medium",   color: "#ca8a04" },
  Low:      { cls: "sev-low",      color: "#16a34a" },
};

function SeverityBadge({ value }) {
  const meta = SEVERITY_META[value] || { cls: "sev-low", color: "#6b7280" };
  return <span className={`rb-sev-badge ${meta.cls}`}>{value}</span>;
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button type="button" className="rb-copy-btn" onClick={handleCopy} title="Copy command">
      {copied ? (
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2.5">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )}
    </button>
  );
}

// ── stats strip ──────────────────────────────────────────────────────────────

function StatsStrip({ results, family, query }) {
  const critical = results.filter(e => e.severity === "Critical").length;
  const families = new Set(results.map(e => e.family)).size;
  return (
    <div className="rb-stats-strip">
      <div className="rb-stat-pill">
        <strong>{results.length}</strong>
        <span>{family === "All" && !query ? "total references" : "matching references"}</span>
      </div>
      <div className="rb-stat-pill rb-stat-pill--warn">
        <strong>{critical}</strong>
        <span>critical severity</span>
      </div>
      <div className="rb-stat-pill">
        <strong>{families}</strong>
        <span>platform {families === 1 ? "family" : "families"}</span>
      </div>
      <div className="rb-stat-pill rb-stat-pill--muted">
        <strong>{rulebookStats.lastUpdated}</strong>
        <span>last reviewed</span>
      </div>
    </div>
  );
}

// ── entry card ───────────────────────────────────────────────────────────────

function EntryCard({ entry, expanded, onToggle, query }) {
  const meta = SEVERITY_META[entry.severity] || { cls: "sev-low", color: "#6b7280" };
  return (
    <article className={`rulebook-entry ${expanded ? "expanded" : ""}`} key={entry.id}>
      <button
        className="rulebook-entry__summary"
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <div className={`rulebook-family rulebook-family--${entry.family.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
          {entry.family}
        </div>
        <div className="rulebook-entry__main">
          <div className="rulebook-entry__title-row">
            <h3>{highlight(entry.title, query)}</h3>
            <SeverityBadge value={entry.severity} />
          </div>
          <p>{highlight(entry.summary, query)}</p>
          <div className="rulebook-entry__meta">
            <span>{entry.versions}</span>
            <span>{entry.status}</span>
            {entry.lastUpdated && <span className="rb-updated-pill">Updated {entry.lastUpdated}</span>}
          </div>
          {entry.affectedComponents?.length > 0 && (
            <div className="rb-components-row">
              {entry.affectedComponents.slice(0, 4).map(c => (
                <span key={c} className="rb-component-chip">{c}</span>
              ))}
              {entry.affectedComponents.length > 4 && (
                <span className="rb-component-chip rb-component-chip--more">
                  +{entry.affectedComponents.length - 4} more
                </span>
              )}
            </div>
          )}
        </div>
        <svg className="rulebook-chevron" viewBox="0 0 24 24" aria-hidden="true">
          <path d="m9 18 6-6-6-6" />
        </svg>
      </button>

      {expanded && (
        <div className="rulebook-entry__details">

          {/* Description */}
          {entry.description && (
            <div className="rb-detail-section rb-detail-section--full">
              <h4>Overview</h4>
              <p className="rb-description">{highlight(entry.description, query)}</p>
            </div>
          )}

          {/* Requirements */}
          <div className="rulebook-guidance">
            <h4>Compatibility checks</h4>
            <ul>{entry.requirements.map(item => <li key={item}>{highlight(item, query)}</li>)}</ul>
          </div>

          {/* Commands */}
          <div className="rulebook-commands">
            <h4>Verification commands</h4>
            {entry.checks.map(check => (
              <div key={check.command} className="rb-command-row">
                <div className="rb-command-meta">
                  <span>{check.label}</span>
                  <CopyButton text={check.command} />
                </div>
                <code>{check.command}</code>
              </div>
            ))}
          </div>

          {/* Known issues */}
          {entry.knownIssues?.length > 0 && (
            <div className="rb-known-issues rb-detail-section--full">
              <h4>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ea580c" strokeWidth="2.5" style={{ marginRight: 5, verticalAlign: "middle" }}>
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                Known issues &amp; gotchas
              </h4>
              <ul className="rb-issues-list">
                {entry.knownIssues.map(issue => (
                  <li key={issue}>{highlight(issue, query)}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Footer */}
          <div className="rulebook-entry__footer">
            <div className="rulebook-tags">
              {entry.tags.map(tag => <span key={tag}>{tag}</span>)}
            </div>
            <a href={entry.sourceUrl} target="_blank" rel="noreferrer">
              {entry.sourceLabel}<span aria-hidden="true"> ↗</span>
            </a>
          </div>
        </div>
      )}
    </article>
  );
}

// ── ask answer panel ─────────────────────────────────────────────────────────

function AskAnswerPanel({ answer, loading, error, question }) {
  if (loading) {
    return (
      <section className="rulebook-answer ask-answer" aria-live="polite">
        <div className="rulebook-answer__icon rb-asking-icon">
          <span className="rb-ask-spinner" />
        </div>
        <div>
          <span>Compatibility Assistant</span>
          <h3>Thinking…</h3>
          <p className="rb-asking-text">Querying the llama model for: <em>{question}</em></p>
        </div>
      </section>
    );
  }
  if (error) {
    return (
      <section className="rulebook-answer ask-answer ask-answer--error" aria-live="polite">
        <div className="rulebook-answer__icon">!</div>
        <div>
          <span>Compatibility Assistant</span>
          <h3>Unable to answer</h3>
          <p>{error}</p>
        </div>
      </section>
    );
  }
  if (!answer) return null;
  return (
    <section className="rulebook-answer ask-answer" aria-live="polite">
      <div className="rulebook-answer__icon rb-ai-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <rect x="3" y="11" width="18" height="10" rx="2"/>
          <circle cx="12" cy="5" r="2"/>
          <path d="M12 7v4"/>
        </svg>
      </div>
      <div>
        <span>Llama Compatibility Assistant</span>
        <h3>Answer</h3>
        <p className="rb-ask-answer-text">{answer}</p>
        <p className="rb-ask-disclaimer">
          This answer is AI-generated. Always verify against official vendor documentation before applying changes.
        </p>
      </div>
    </section>
  );
}

// ── main component ───────────────────────────────────────────────────────────

export default function CompatibilityRulebook() {
  const [query, setQuery]           = useState("");
  const [family, setFamily]         = useState("All");
  const [expandedId, setExpandedId] = useState(rulebookEntries[0].id);
  const [sortBy, setSortBy]         = useState("relevance"); // "relevance" | "severity" | "updated"
  const [mode, setMode]             = useState("search");    // "search" | "ask"

  // Ask state
  const [askAnswer, setAskAnswer]   = useState(null);
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError]     = useState(null);
  const [lastAsked, setLastAsked]   = useState("");

  const inputRef = useRef(null);

  // ── filtered + sorted results ──────────────────────────────────────────────
  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const terms = normalized.split(/\s+/).filter(Boolean);

    let entries = rulebookEntries.filter(e => family === "All" || e.family === family);

    if (terms.length) {
      entries = entries
        .map(entry => {
          const hay = searchableText(entry);
          const score = terms.reduce((acc, t) => acc + (hay.includes(t) ? 1 : 0), 0);
          return { entry, score };
        })
        .filter(item => item.score === terms.length)
        .sort((a, b) => b.score - a.score)
        .map(item => item.entry);
    }

    if (sortBy === "severity") {
      entries = [...entries].sort((a, b) =>
        (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99)
      );
    } else if (sortBy === "updated") {
      entries = [...entries].sort((a, b) => (b.lastUpdated || "").localeCompare(a.lastUpdated || ""));
    } else {
      // relevance: already sorted by score; if no query, sort by severity
      if (!terms.length) {
        entries = [...entries].sort((a, b) =>
          (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99)
        );
      }
    }

    return entries;
  }, [family, query, sortBy]);

  const bestMatch = query.trim() && mode === "search" ? results[0] : null;

  // ── ask handler ────────────────────────────────────────────────────────────
  const handleAsk = async () => {
    const q = query.trim();
    if (!q || askLoading) return;
    setAskLoading(true);
    setAskAnswer(null);
    setAskError(null);
    setLastAsked(q);
    try {
      const res = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (res.ok) {
        const data = await res.json();
        setAskAnswer(data.answer || "No answer returned.");
      } else {
        setAskError("The compatibility assistant returned an error. Please try again.");
      }
    } catch {
      setAskError("Could not reach the backend. Make sure the API is running.");
    } finally {
      setAskLoading(false);
    }
  };

  const clearAll = () => {
    setQuery("");
    setAskAnswer(null);
    setAskError(null);
    setLastAsked("");
    inputRef.current?.focus();
  };

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div className="rulebook-page">

      {/* ── intro ── */}
      <section className="rulebook-intro">
        <div>
          <span className="rulebook-eyebrow">Built-in operations reference</span>
          <h2>Compatibility Rulebook</h2>
          <p>
            Find platform requirements, version boundaries, known issues, verification commands,
            and official vendor references before approving a compatibility rule. Ask the
            on-premise Llama assistant for direct answers.
          </p>
        </div>
        <div className="rulebook-updated">
          <span>Reference edition</span>
          <strong>June 2026</strong>
        </div>
      </section>

      {/* ── summary cards ── */}
      <div className="rb-summary-cards">
        <div className="rb-summary-card rb-summary-card--primary">
          <div className="rb-summary-card__value">{rulebookStats.totalEntries}</div>
          <div className="rb-summary-card__label">Reference entries</div>
          <div className="rb-summary-card__sub">{rulebookStats.families} platform families</div>
        </div>
        <div className="rb-summary-card rb-summary-card--danger">
          <div className="rb-summary-card__value">{rulebookStats.criticalEntries}</div>
          <div className="rb-summary-card__label">Critical severity</div>
          <div className="rb-summary-card__sub">Requires immediate validation</div>
        </div>
        <div className="rb-summary-card rb-summary-card--info">
          <div className="rb-summary-card__value">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="10" rx="2"/>
              <circle cx="12" cy="5" r="2"/><path d="M12 7v4"/>
            </svg>
          </div>
          <div className="rb-summary-card__label">AI Ask mode</div>
          <div className="rb-summary-card__sub">Powered by llama3.2:3b</div>
        </div>
        <div className="rb-summary-card rb-summary-card--neutral">
          <div className="rb-summary-card__value">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
            </svg>
          </div>
          <div className="rb-summary-card__label">Verification commands</div>
          <div className="rb-summary-card__sub">Copy-ready CLI snippets</div>
        </div>
      </div>

      {/* ── search / ask band ── */}
      <section className="rulebook-search-band" aria-label="Rulebook search">
        <div className="rulebook-search-wrapper">

          {/* Mode toggle */}
          <div className="rulebook-mode-toggle" role="group" aria-label="Mode">
            <button
              type="button"
              className={mode === "search" ? "active" : ""}
              onClick={() => { setMode("search"); setAskAnswer(null); setAskError(null); }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="11" cy="11" r="8"/><path d="m20 20-3.5-3.5"/>
              </svg>
              Search
            </button>
            <button
              type="button"
              className={mode === "ask" ? "active" : ""}
              onClick={() => setMode("ask")}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <rect x="3" y="11" width="18" height="10" rx="2"/>
                <circle cx="12" cy="5" r="2"/><path d="M12 7v4"/>
              </svg>
              Ask AI
            </button>
          </div>

          {/* Input */}
          <label className="rulebook-search">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>
            </svg>
            <input
              ref={inputRef}
              value={query}
              onChange={e => { setQuery(e.target.value); if (mode === "ask") { setAskAnswer(null); setAskError(null); } }}
              placeholder={mode === "search" ? "Search for TPM, Ubuntu LTS, CUDA, ESXi…" : "Ask a compatibility question… (press Enter or click Ask)"}
              aria-label={mode === "search" ? "Search compatibility rulebook" : "Ask compatibility question"}
              onKeyDown={e => { if (e.key === "Enter" && mode === "ask") handleAsk(); }}
            />
            {query && (
              <button type="button" onClick={clearAll} aria-label="Clear" className="rb-clear-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            )}
            {mode === "ask" && (
              <button
                type="button"
                className="rb-ask-send-btn"
                onClick={handleAsk}
                disabled={askLoading || !query.trim()}
                aria-label="Send question"
              >
                {askLoading ? (
                  <span className="rb-ask-spinner rb-ask-spinner--sm" />
                ) : (
                  <>
                    Ask
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ marginLeft: 4 }}>
                      <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                  </>
                )}
              </button>
            )}
          </label>

          {/* Ask mode hint */}
          {mode === "ask" && (
            <p className="rb-ask-hint">
              Powered by <strong>llama3.2:3b</strong> running on-premise via Ollama. Answers are direct and concise.
            </p>
          )}
        </div>

        {/* Family filter tabs */}
        <div className="rulebook-filters" role="tablist" aria-label="Platform family">
          {rulebookFamilies.map(item => (
            <button
              key={item}
              type="button"
              className={family === item ? "active" : ""}
              onClick={() => setFamily(item)}
              role="tab"
              aria-selected={family === item}
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      {/* ── best match (search mode) ── */}
      {mode === "search" && bestMatch && (
        <section className="rulebook-answer" aria-live="polite">
          <div className="rulebook-answer__icon">A</div>
          <div>
            <span>Best matching guidance</span>
            <h3>{bestMatch.title}</h3>
            <p>{highlight(bestMatch.summary, query)}</p>
            <button type="button" onClick={() => setExpandedId(bestMatch.id)}>
              Open full guidance ↓
            </button>
          </div>
        </section>
      )}

      {/* ── ask answer ── */}
      {mode === "ask" && (askAnswer || askLoading || askError) && (
        <AskAnswerPanel
          answer={askAnswer}
          loading={askLoading}
          error={askError}
          question={lastAsked}
        />
      )}

      {/* ── search results ── */}
      {mode === "search" && (
        <>
          {/* Results header with sort */}
          <div className="rulebook-results-head">
            <StatsStrip results={results} family={family} query={query} />
            <div className="rb-sort-row">
              <label htmlFor="rb-sort">Sort by</label>
              <select
                id="rb-sort"
                className="rb-sort-select"
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
              >
                <option value="relevance">Relevance / Severity</option>
                <option value="severity">Severity (Critical first)</option>
                <option value="updated">Last updated</option>
              </select>
            </div>
          </div>

          {results.length ? (
            <div className="rulebook-grid">
              {results.map(entry => (
                <EntryCard
                  key={entry.id}
                  entry={entry}
                  expanded={expandedId === entry.id}
                  onToggle={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                  query={query}
                />
              ))}
            </div>
          ) : (
            <section className="rulebook-empty">
              <strong>No matching guidance</strong>
              <p>
                Try a platform, component, or requirement such as "Secure Boot", "kernel",
                "CUDA", "version skew", or "iDRAC".
              </p>
              <button type="button" onClick={clearAll}>Reset search</button>
            </section>
          )}
        </>
      )}

      {/* ── ask mode: still show entries below ── */}
      {mode === "ask" && (
        <>
          <div className="rulebook-results-head" style={{ marginTop: 16 }}>
            <StatsStrip results={results} family={family} query={query} />
          </div>
          <div className="rb-ask-browse-label">
            Browse reference entries — or switch to Search mode for keyword filtering.
          </div>
          <div className="rulebook-grid">
            {results.map(entry => (
              <EntryCard
                key={entry.id}
                entry={entry}
                expanded={expandedId === entry.id}
                onToggle={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                query={query}
              />
            ))}
          </div>
        </>
      )}

      <footer className="rulebook-note">
        This rulebook is an operational starting point, not a substitute for vendor certification.
        Support windows and compatibility matrices change over time. Always verify with the linked source.
      </footer>
    </div>
  );
}
