"""Async link checker built on aiohttp — verifies status codes for many links in parallel."""
from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import aiohttp

from ..config import get_settings
from ..schemas import LinkStatus


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


async def _check_one(session: aiohttp.ClientSession, sem: asyncio.Semaphore, url: str, base_domain: str) -> LinkStatus:
    internal = _domain(url) == base_domain
    async with sem:
        try:
            # HEAD first (cheap); fall back to GET if the server rejects HEAD.
            async with session.head(url, allow_redirects=True) as resp:
                status = resp.status
            if status >= 400 or status == 405:
                async with session.get(url, allow_redirects=True) as resp:
                    status = resp.status
            return LinkStatus(url=url, status=status, ok=status < 400, internal=internal)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            return LinkStatus(url=url, status=None, ok=False, internal=internal, error=str(e) or type(e).__name__)


async def check_links(links: set[str], base_domain: str, on_progress=None) -> tuple[list[LinkStatus], int]:
    """
    Check every link's HTTP status. Returns (broken_links, total_checked).
    `on_progress` is an optional async callback(done:int, total:int).
    """
    cfg = get_settings()
    links = list(links)
    total = len(links)
    if not total:
        return [], 0

    sem = asyncio.Semaphore(cfg.link_check_concurrency)
    timeout = aiohttp.ClientTimeout(total=cfg.request_timeout)
    headers = {"User-Agent": cfg.user_agent}
    broken: list[LinkStatus] = []

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        tasks = [asyncio.ensure_future(_check_one(session, sem, u, base_domain)) for u in links]
        done = 0
        for fut in asyncio.as_completed(tasks):
            res = await fut
            done += 1
            if not res.ok:
                broken.append(res)
            if on_progress:
                await on_progress(done, total)

    return broken, total
