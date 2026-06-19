// Thin API client for the SeoTuners audit backend.

export async function health() {
  const r = await fetch("/api/health");
  return r.json();
}

export async function startAudit(url, options) {
  const r = await fetch("/api/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, options }),
  });
  if (!r.ok) throw new Error((await r.json()).detail || "Failed to start audit");
  return r.json(); // { id, status }
}

export async function getAudit(id) {
  const r = await fetch(`/api/audits/${id}`);
  if (!r.ok) throw new Error("Audit not found");
  return r.json();
}

export function reportHtmlUrl(id) {
  return `/api/audits/${id}/report.html`;
}
export function reportPdfUrl(id) {
  return `/api/audits/${id}/report.pdf`;
}

// Subscribe to live progress via WebSocket. Returns a close() function.
export function subscribeProgress(id, onEvent, onDone) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/audits/${id}`);
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    onEvent(data);
    if (data.status === "done" || data.status === "error") onDone?.(data);
  };
  ws.onclose = () => onDone?.();
  ws.onerror = () => onDone?.();
  return () => ws.close();
}
