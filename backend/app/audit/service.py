"""Audit orchestration: crawl -> link check -> rules -> AI -> result, with live progress.

Jobs are tracked in an in-memory store keyed by id. Each job has an asyncio.Queue of
ProgressEvents that the WebSocket endpoint streams to the dashboard. Swap `AUDITS` for a
DB/Redis-backed store for multi-worker deployments (see db.py for the persistence model).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from ..analysis import analyze_with_ai, rule_based_analysis
from ..config import get_settings
from ..crawler import check_links, crawl
from ..schemas import AuditOptions, AuditResult, AuditStatus, ProgressEvent

AUDITS: dict[str, AuditResult] = {}
_QUEUES: dict[str, asyncio.Queue[ProgressEvent | None]] = {}


def get_audit(audit_id: str) -> AuditResult | None:
    return AUDITS.get(audit_id)


def get_queue(audit_id: str) -> asyncio.Queue | None:
    return _QUEUES.get(audit_id)


async def _emit(audit_id: str, status: AuditStatus, message: str, pct: int) -> None:
    audit = AUDITS.get(audit_id)
    if audit:
        audit.status = status
    q = _QUEUES.get(audit_id)
    if q:
        await q.put(ProgressEvent(status=status, message=message, pct=pct))


def start_audit(url: str, options: AuditOptions) -> str:
    """Register a new audit job and kick off the background task. Returns the audit id."""
    audit_id = uuid.uuid4().hex[:12]
    AUDITS[audit_id] = AuditResult(
        id=audit_id,
        url=url,
        client_name=options.client_name,
        status=AuditStatus.queued,
        created_at=datetime.now(timezone.utc),
    )
    _QUEUES[audit_id] = asyncio.Queue()
    asyncio.create_task(run_audit(audit_id, url, options))
    return audit_id


async def run_audit(audit_id: str, url: str, options: AuditOptions) -> AuditResult:
    cfg = get_settings()
    audit = AUDITS[audit_id]
    try:
        # 1. crawl
        await _emit(audit_id, AuditStatus.crawling, f"Crawling {url}…", 5)

        async def on_page(done, total, page_url):
            pct = 5 + int(35 * done / max(total, 1))
            await _emit(audit_id, AuditStatus.crawling, f"Crawled {done}/{total}: {page_url}", pct)

        crawl_result, links = await crawl(url, options.max_pages, on_page=on_page)
        audit.crawl = crawl_result

        # 2. link check
        if options.check_links and links:
            await _emit(audit_id, AuditStatus.checking_links, f"Checking {len(links)} links…", 45)

            async def on_link(done, total):
                pct = 45 + int(25 * done / max(total, 1))
                await _emit(audit_id, AuditStatus.checking_links, f"Checked {done}/{total} links", pct)

            broken, checked = await check_links(links, crawl_result.domain, on_progress=on_link)
            crawl_result.broken_links = broken
            crawl_result.links_checked = checked

        # 3. rule-based analysis (always)
        await _emit(audit_id, AuditStatus.analyzing, "Running SEO checks…", 72)
        rules = rule_based_analysis(crawl_result)

        # 4. AI analysis (optional)
        analysis = rules
        if options.use_ai and cfg.ai_enabled:
            await _emit(audit_id, AuditStatus.analyzing, f"Analysing with {cfg.ai_model}…", 80)
            try:
                analysis = await asyncio.to_thread(analyze_with_ai, crawl_result, rules)
            except Exception as e:  # never let an AI hiccup kill the audit — fall back to rules
                await _emit(audit_id, AuditStatus.analyzing, f"AI step failed ({e}); using rule-based report.", 88)
                analysis = rules
        elif options.use_ai and not cfg.ai_enabled:
            await _emit(audit_id, AuditStatus.analyzing, "No AI key set — using rule-based report.", 85)

        audit.analysis = analysis
        audit.score = analysis.score

        # 5. done
        await _emit(audit_id, AuditStatus.building_report, "Building report…", 95)
        audit.status = AuditStatus.done
        await _emit(audit_id, AuditStatus.done, "Audit complete.", 100)
    except Exception as e:
        audit.status = AuditStatus.error
        audit.error = str(e)
        await _emit(audit_id, AuditStatus.error, f"Audit failed: {e}", 100)
    finally:
        q = _QUEUES.get(audit_id)
        if q:
            await q.put(None)  # sentinel: stream complete
    return audit
