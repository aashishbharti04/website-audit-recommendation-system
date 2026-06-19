"""Deterministic, rule-based SEO checks. Produces issues with zero external dependencies.

This runs always — it gives the tool real value even without an AI key, and gives
the AI layer a verified set of findings to expand on rather than hallucinate.
"""
from __future__ import annotations

from ..schemas import AIAnalysis, Category, CrawlResult, Issue, Severity


def rule_based_analysis(crawl: CrawlResult) -> AIAnalysis:
    issues: list[Issue] = []
    pages = [p for p in crawl.pages if not p.error]
    n = len(pages) or 1

    def add(title, cat, sev, desc, rec, affected=None):
        issues.append(Issue(title=title, category=cat, severity=sev, description=desc, recommendation=rec, affected=affected))

    # --- titles ---
    missing_title = [p.url for p in pages if not p.title]
    if missing_title:
        add("Missing page titles", Category.on_page, Severity.critical,
            f"{len(missing_title)} page(s) have no <title> tag.",
            "Add a unique, descriptive 50–60 character title to every page.",
            _sample(missing_title))
    long_title = [p.url for p in pages if p.title and p.title_length > 60]
    if long_title:
        add("Title tags too long", Category.on_page, Severity.low,
            f"{len(long_title)} title(s) exceed 60 characters and may be truncated in search results.",
            "Trim titles to ~60 characters, keeping the primary keyword near the front.",
            _sample(long_title))

    # --- meta descriptions ---
    no_meta = [p.url for p in pages if not p.meta_description]
    if no_meta:
        add("Missing meta descriptions", Category.on_page, Severity.high,
            f"{len(no_meta)} page(s) lack a meta description.",
            "Write a compelling 140–160 character meta description for each page to improve click-through.",
            _sample(no_meta))

    # --- H1 ---
    no_h1 = [p.url for p in pages if not p.h1]
    if no_h1:
        add("Missing H1 heading", Category.on_page, Severity.high,
            f"{len(no_h1)} page(s) have no H1 heading.",
            "Add exactly one H1 per page that describes the page's main topic.",
            _sample(no_h1))
    multi_h1 = [p.url for p in pages if len(p.h1) > 1]
    if multi_h1:
        add("Multiple H1 headings", Category.on_page, Severity.low,
            f"{len(multi_h1)} page(s) have more than one H1.",
            "Use a single H1 per page; demote the others to H2/H3.",
            _sample(multi_h1))

    # --- canonical ---
    no_canon = [p.url for p in pages if not p.canonical]
    if no_canon:
        add("Missing canonical tags", Category.technical, Severity.medium,
            f"{len(no_canon)} page(s) have no canonical link, risking duplicate-content dilution.",
            "Add a self-referencing <link rel=\"canonical\"> to each page.",
            _sample(no_canon))

    # --- thin content ---
    thin = [p.url for p in pages if p.word_count < 300]
    if thin:
        add("Thin content", Category.content, Severity.medium,
            f"{len(thin)} page(s) have under 300 words and may be seen as low value.",
            "Expand thin pages with useful, original content of at least 600–800 words where relevant.",
            _sample(thin))

    # --- images / alt ---
    missing_alt = sum(p.images_missing_alt for p in pages)
    if missing_alt:
        add("Images missing alt text", Category.on_page, Severity.medium,
            f"{missing_alt} image(s) across the site are missing alt attributes.",
            "Add descriptive alt text to every meaningful image for accessibility and image SEO.")

    # --- mobile ---
    no_viewport = [p.url for p in pages if not p.has_viewport]
    if no_viewport:
        add("Missing mobile viewport", Category.mobile, Severity.high,
            f"{len(no_viewport)} page(s) lack a responsive viewport meta tag.",
            "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> to all pages.",
            _sample(no_viewport))

    # --- structured data / OG ---
    no_schema = [p.url for p in pages if not p.has_schema]
    if len(no_schema) == len(pages):
        add("No structured data", Category.structured_data, Severity.medium,
            "No Schema.org / JSON-LD structured data was found on the site.",
            "Add relevant structured data (Organization, BreadcrumbList, Article, Product, etc.) to earn rich results.")
    no_og = [p.url for p in pages if not p.has_open_graph]
    if no_og:
        add("Missing Open Graph tags", Category.technical, Severity.low,
            f"{len(no_og)} page(s) lack Open Graph tags for social sharing.",
            "Add og:title, og:description and og:image so shared links render attractively.",
            _sample(no_og))

    # --- performance (rough, from load time) ---
    slow = [p.url for p in pages if p.load_ms and p.load_ms > 2500]
    if slow:
        add("Slow page responses", Category.performance, Severity.medium,
            f"{len(slow)} page(s) took over 2.5s to respond during the crawl.",
            "Investigate server response time, caching, and payload size; aim for sub-1s TTFB.",
            _sample(slow))

    # --- broken links ---
    if crawl.broken_links:
        internal_broken = [b.url for b in crawl.broken_links if b.internal]
        add("Broken links", Category.links,
            Severity.high if internal_broken else Severity.medium,
            f"{len(crawl.broken_links)} broken link(s) found ({len(internal_broken)} internal).",
            "Fix or remove broken links and set up 301 redirects where pages have moved.",
            _sample([b.url for b in crawl.broken_links]))

    # --- crawl errors ---
    errored = [p.url for p in crawl.pages if p.error]
    if errored:
        add("Pages failed to load", Category.technical, Severity.high,
            f"{len(errored)} URL(s) could not be fetched during the crawl.",
            "Ensure all linked pages return 200 and are reachable by crawlers.",
            _sample(errored))

    score = _score(issues, n)
    summary = (
        f"Scanned {len(crawl.pages)} page(s) on {crawl.domain}. "
        f"Found {len(issues)} issue type(s). Overall SEO health score: {score}/100."
    )
    quick = [i.recommendation for i in sorted(issues, key=_sev_rank)[:5]]
    return AIAnalysis(executive_summary=summary, score=score, issues=issues, quick_wins=quick)


_SEV_WEIGHT = {Severity.critical: 18, Severity.high: 10, Severity.medium: 5, Severity.low: 2, Severity.info: 0}


def _sev_rank(issue: Issue) -> int:
    order = [Severity.critical, Severity.high, Severity.medium, Severity.low, Severity.info]
    return order.index(issue.severity)


def _score(issues: list[Issue], n_pages: int) -> int:
    penalty = sum(_SEV_WEIGHT[i.severity] for i in issues)
    return max(0, min(100, 100 - penalty))


def _sample(urls: list[str], k: int = 5) -> str:
    shown = urls[:k]
    extra = len(urls) - len(shown)
    text = ", ".join(shown)
    return text + (f" (+{extra} more)" if extra > 0 else "")
