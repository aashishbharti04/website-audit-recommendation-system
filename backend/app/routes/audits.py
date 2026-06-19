"""REST endpoints for creating audits, fetching results, and exporting reports."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from ..audit import get_audit, start_audit
from ..report import render_html, render_pdf, weasyprint_available
from ..schemas import AuditRequest, AuditResult

router = APIRouter(prefix="/api/audits", tags=["audits"])


@router.post("", status_code=202)
async def create_audit(req: AuditRequest) -> dict:
    """Start a new audit. Returns the audit id; poll the result or subscribe via WebSocket.

    Must be async: start_audit schedules the background job with asyncio.create_task,
    which requires a running event loop (a sync endpoint would run in a threadpool).
    """
    if not req.url.strip():
        raise HTTPException(400, "A URL is required.")
    audit_id = start_audit(req.url.strip(), req.options)
    return {"id": audit_id, "status": "queued"}


@router.get("/{audit_id}", response_model=AuditResult)
def read_audit(audit_id: str) -> AuditResult:
    audit = get_audit(audit_id)
    if not audit:
        raise HTTPException(404, "Audit not found.")
    return audit


@router.get("/{audit_id}/report.html", response_class=HTMLResponse)
def report_html(audit_id: str) -> HTMLResponse:
    audit = _require_done(audit_id)
    return HTMLResponse(render_html(audit))


@router.get("/{audit_id}/report.pdf")
def report_pdf(audit_id: str) -> Response:
    audit = _require_done(audit_id)
    if not weasyprint_available():
        raise HTTPException(
            501,
            "PDF export unavailable on this server (WeasyPrint native deps missing). "
            "Use /report.html instead.",
        )
    pdf = render_pdf(audit)
    domain = audit.crawl.domain if audit.crawl else "site"
    filename = f"seo-audit-{domain}.pdf"
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _require_done(audit_id: str) -> AuditResult:
    audit = get_audit(audit_id)
    if not audit:
        raise HTTPException(404, "Audit not found.")
    if audit.status.value != "done":
        raise HTTPException(409, f"Audit not finished (status: {audit.status.value}).")
    return audit
