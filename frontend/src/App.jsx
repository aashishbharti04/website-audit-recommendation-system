import React, { useEffect, useState } from "react";
import { getAudit, health, startAudit, subscribeProgress } from "./api.js";
import UrlForm from "./components/UrlForm.jsx";
import ProgressLog from "./components/ProgressLog.jsx";
import ReportView from "./components/ReportView.jsx";

export default function App() {
  const [info, setInfo] = useState(null);
  const [events, setEvents] = useState([]);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => { health().then(setInfo).catch(() => {}); }, []);

  const busy = ["queued", "crawling", "checking_links", "analyzing", "building_report"].includes(status);

  const onStart = async (url, options) => {
    setError(null); setAudit(null); setEvents([]); setPct(0); setStatus("queued");
    try {
      const { id } = await startAudit(url, options);
      const close = subscribeProgress(
        id,
        (ev) => { setEvents((prev) => [...prev, ev]); setPct(ev.pct); setStatus(ev.status); },
        async (last) => {
          close?.();
          if (!last || last.status === "done") {
            try { setAudit(await getAudit(id)); setStatus("done"); }
            catch (e) { setError(String(e)); }
          } else if (last.status === "error") {
            setStatus("error"); setError(last.message);
          }
        }
      );
    } catch (e) {
      setStatus("error"); setError(String(e.message || e));
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">🔍</span>
          <div>
            <strong>{info?.agency || "SeoTuners"}</strong>
            <small>SEO Audit Studio</small>
          </div>
        </div>
        {info && (
          <div className="badges">
            <span className={`badge ${info.ai_enabled ? "ok" : "off"}`}>
              AI {info.ai_enabled ? `· ${info.ai_model}` : "off"}
            </span>
            <span className={`badge ${info.pdf_enabled ? "ok" : "off"}`}>
              PDF {info.pdf_enabled ? "on" : "off"}
            </span>
          </div>
        )}
      </header>

      <main className="main">
        <UrlForm onStart={onStart} busy={busy} />
        {error && <div className="card error">⚠️ {error}</div>}
        <ProgressLog events={events} pct={pct} status={status} />
        {audit && audit.status === "done" && <ReportView audit={audit} />}
      </main>

      <footer className="footer">
        Internal tool · {info?.agency || "SeoTuners"} · crawls, analyses & reports — your data stays on your server.
      </footer>
    </div>
  );
}
