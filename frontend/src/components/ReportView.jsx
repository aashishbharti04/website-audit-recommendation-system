import React, { useState } from "react";
import { reportHtmlUrl, reportPdfUrl } from "../api.js";

const SEV_ORDER = ["critical", "high", "medium", "low", "info"];
const SEV_COLOR = {
  critical: "#dc2626", high: "#ea580c", medium: "#d97706", low: "#2563eb", info: "#6b7280",
};

export default function ReportView({ audit }) {
  const [filter, setFilter] = useState("all");
  const a = audit.analysis;
  if (!a) return null;

  const score = audit.score ?? a.score ?? 0;
  const scoreColor = score >= 80 ? "#16a34a" : score >= 50 ? "#d97706" : "#dc2626";

  const counts = {};
  a.issues.forEach((i) => (counts[i.severity] = (counts[i.severity] || 0) + 1));

  const issues = filter === "all" ? a.issues : a.issues.filter((i) => i.severity === filter);
  const sorted = [...issues].sort((x, y) => SEV_ORDER.indexOf(x.severity) - SEV_ORDER.indexOf(y.severity));

  return (
    <div className="card report">
      <div className="report-top">
        <div className="score" style={{ background: scoreColor }}>
          <b>{score}</b><span>/100</span>
        </div>
        <div className="report-meta">
          <h2>Audit results</h2>
          <p className="summary">{a.executive_summary}</p>
          <div className="exports">
            <a className="btn" href={reportHtmlUrl(audit.id)} target="_blank" rel="noopener">Open HTML report</a>
            <a className="btn primary" href={reportPdfUrl(audit.id)} target="_blank" rel="noopener">Download PDF</a>
          </div>
        </div>
      </div>

      {a.quick_wins?.length > 0 && (
        <div className="wins">
          <h3>⚡ Quick wins</h3>
          <ul>{a.quick_wins.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}

      <div className="filters">
        <button className={`chip ${filter === "all" ? "on" : ""}`} onClick={() => setFilter("all")}>
          All ({a.issues.length})
        </button>
        {SEV_ORDER.filter((s) => counts[s]).map((s) => (
          <button key={s} className={`chip ${filter === s ? "on" : ""}`} onClick={() => setFilter(s)}
            style={filter === s ? { background: SEV_COLOR[s], borderColor: SEV_COLOR[s], color: "#fff" } : {}}>
            {counts[s]} {s}
          </button>
        ))}
      </div>

      <div className="issues">
        {sorted.map((i, idx) => (
          <div key={idx} className="issue" style={{ borderLeftColor: SEV_COLOR[i.severity] }}>
            <div className="issue-head">
              <h4>{i.title} <span className="cat">· {i.category}</span></h4>
              <span className="tag" style={{ background: SEV_COLOR[i.severity] }}>{i.severity}</span>
            </div>
            <p>{i.description}</p>
            <div className="rec"><b>Fix:</b> {i.recommendation}</div>
            {i.affected && <div className="affected">Affected: {i.affected}</div>}
          </div>
        ))}
      </div>

      {audit.crawl?.broken_links?.length > 0 && (
        <div className="broken">
          <h3>Broken links ({audit.crawl.broken_links.length})</h3>
          <table>
            <thead><tr><th>URL</th><th>Status</th><th>Type</th></tr></thead>
            <tbody>
              {audit.crawl.broken_links.slice(0, 30).map((b, i) => (
                <tr key={i}>
                  <td>{b.url}</td>
                  <td>{b.status || b.error || "error"}</td>
                  <td>{b.internal ? "internal" : "external"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
