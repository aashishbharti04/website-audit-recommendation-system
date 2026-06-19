"""Async breadth-first crawler built on httpx. Fetches pages and extracts SEO data."""
from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from ..config import get_settings
from ..schemas import CrawlResult, PageSEO
from .seo_parser import parse_page


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _normalize_start(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


async def _fetch(client: httpx.AsyncClient, url: str) -> tuple[str | None, int | None, int | None, str | None]:
    """Return (html, status, load_ms, error)."""
    start = time.perf_counter()
    try:
        resp = await client.get(url, follow_redirects=True)
        load_ms = int((time.perf_counter() - start) * 1000)
        ctype = resp.headers.get("content-type", "")
        if "text/html" not in ctype:
            return None, resp.status_code, load_ms, f"Not HTML ({ctype or 'unknown'})"
        return resp.text, resp.status_code, load_ms, None
    except httpx.HTTPError as e:
        return None, None, int((time.perf_counter() - start) * 1000), str(e)


async def crawl(start_url: str, max_pages: int = 20, on_page=None) -> tuple[CrawlResult, set[str]]:
    """
    Crawl up to `max_pages` internal pages starting from `start_url`.

    `on_page` is an optional async callback(done:int, total:int, url:str) for progress.
    Returns the CrawlResult plus the full set of discovered links (for link checking).
    """
    cfg = get_settings()
    start_url = _normalize_start(start_url)
    base_domain = _domain(start_url)

    seen: set[str] = {start_url}
    queue: deque[str] = deque([start_url])
    pages: list[PageSEO] = []
    all_links: set[str] = set()

    headers = {"User-Agent": cfg.user_agent}
    limits = httpx.Limits(max_connections=cfg.crawl_concurrency)
    async with httpx.AsyncClient(headers=headers, timeout=cfg.request_timeout, limits=limits) as client:
        while queue and len(pages) < max_pages:
            # pull a batch to fetch concurrently
            batch = [queue.popleft() for _ in range(min(cfg.crawl_concurrency, len(queue), max_pages - len(pages)))]
            results = await asyncio.gather(*[_fetch(client, u) for u in batch])

            for url, (html, status, load_ms, error) in zip(batch, results):
                if error or not html:
                    pages.append(PageSEO(url=url, status=status, error=error))
                    continue
                page, links = parse_page(url, html, status, load_ms, base_domain)
                pages.append(page)
                all_links |= links

                # enqueue new internal links
                for link in links:
                    if link not in seen and _domain(link) == base_domain and len(seen) < max_pages * 5:
                        seen.add(link)
                        queue.append(link)

                if on_page:
                    await on_page(len(pages), max_pages, url)

    result = CrawlResult(
        start_url=start_url,
        domain=base_domain,
        pages=pages,
        crawled_at=datetime.now(timezone.utc),
    )
    return result, all_links
