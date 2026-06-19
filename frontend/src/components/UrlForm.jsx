import React, { useState } from "react";

export default function UrlForm({ onStart, busy }) {
  const [url, setUrl] = useState("");
  const [clientName, setClientName] = useState("");
  const [maxPages, setMaxPages] = useState(20);
  const [checkLinks, setCheckLinks] = useState(true);
  const [useAi, setUseAi] = useState(true);

  const submit = (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    onStart(url.trim(), {
      max_pages: Number(maxPages),
      check_links: checkLinks,
      use_ai: useAi,
      client_name: clientName.trim() || null,
    });
  };

  return (
    <form className="card form" onSubmit={submit}>
      <h2>New audit</h2>
      <div className="row">
        <label className="grow">
          <span>Client website URL *</span>
          <input
            type="text"
            placeholder="example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={busy}
            required
          />
        </label>
        <label>
          <span>Client name</span>
          <input
            type="text"
            placeholder="Acme Inc."
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
            disabled={busy}
          />
        </label>
      </div>
      <div className="row opts">
        <label className="num">
          <span>Max pages</span>
          <input type="number" min="1" max="200" value={maxPages}
            onChange={(e) => setMaxPages(e.target.value)} disabled={busy} />
        </label>
        <label className="check">
          <input type="checkbox" checked={checkLinks}
            onChange={(e) => setCheckLinks(e.target.checked)} disabled={busy} />
          <span>Check links</span>
        </label>
        <label className="check">
          <input type="checkbox" checked={useAi}
            onChange={(e) => setUseAi(e.target.checked)} disabled={busy} />
          <span>AI analysis</span>
        </label>
        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? "Auditing…" : "Run audit"}
        </button>
      </div>
    </form>
  );
}
