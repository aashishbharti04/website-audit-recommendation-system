"""AI analysis layer — sends the real crawl data to Claude and gets back a
prioritised, validated issues list via structured outputs (no parsing, no hallucinated shape).

Uses the official Anthropic Python SDK with `messages.parse()` so the response is
guaranteed to match the `AIAnalysis` Pydantic schema.
"""
from __future__ import annotations

import json

from ..config import get_settings
from ..schemas import AIAnalysis, CrawlResult

SYSTEM_PROMPT = """You are a senior technical SEO auditor at a digital marketing agency.
You are given real crawl data from a client's website (already collected by a crawler —
do not invent pages or facts not present in the data).

Produce a professional, client-ready audit:
- Write a concise executive summary a non-technical business owner can understand.
- Give an overall SEO health score from 0-100 grounded in the severity and number of issues.
- List concrete, prioritised issues (most severe first). For each: a clear title, the category,
  a severity, a plain-English description of the impact, and a specific, actionable fix.
- Base every issue on the supplied data. Where the rule-based findings already flag something,
  refine and explain it rather than repeating it verbatim; add issues the rules may have missed
  (e.g. keyword/title quality, content gaps, internal-linking structure, intent mismatch).
- End with 3-5 highest-impact "quick wins" the client should do first.
Be specific and honest. Do not pad the report with generic advice that isn't supported by the data."""


def summarize_crawl(crawl: CrawlResult, rule_findings: AIAnalysis | None = None) -> dict:
    """Compact the crawl into a JSON-friendly payload for the model (keeps tokens reasonable)."""
    pages = []
    for p in crawl.pages[:60]:  # cap for token budget
        pages.append({
            "url": p.url,
            "status": p.status,
            "title": p.title,
            "title_length": p.title_length,
            "meta_description_length": p.meta_description_length,
            "h1": p.h1[:3],
            "h2_count": p.h2_count,
            "canonical": bool(p.canonical),
            "robots_meta": p.robots_meta,
            "word_count": p.word_count,
            "images_total": p.images_total,
            "images_missing_alt": p.images_missing_alt,
            "has_viewport": p.has_viewport,
            "has_open_graph": p.has_open_graph,
            "has_schema": p.has_schema,
            "load_ms": p.load_ms,
            "error": p.error,
        })
    payload = {
        "domain": crawl.domain,
        "pages_crawled": len(crawl.pages),
        "links_checked": crawl.links_checked,
        "broken_links": [{"url": b.url, "status": b.status, "internal": b.internal} for b in crawl.broken_links[:30]],
        "pages": pages,
    }
    if rule_findings:
        payload["rule_based_findings"] = [
            {"title": i.title, "category": i.category.value, "severity": i.severity.value, "affected": i.affected}
            for i in rule_findings.issues
        ]
    return payload


def analyze_with_ai(crawl: CrawlResult, rule_findings: AIAnalysis | None = None) -> AIAnalysis:
    """Run the Claude analysis. Raises if no API key is configured (caller should check first)."""
    import anthropic

    cfg = get_settings()
    if not cfg.ai_enabled:
        raise RuntimeError("ANTHROPIC_API_KEY is not set; AI analysis unavailable.")

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    payload = summarize_crawl(crawl, rule_findings)

    response = client.messages.parse(
        model=cfg.ai_model,
        max_tokens=cfg.ai_max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                "Here is the crawl data for the audit. Return the structured audit.\n\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
        }],
        output_format=AIAnalysis,
    )
    return response.parsed_output
