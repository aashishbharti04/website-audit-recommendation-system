"""Unit tests for the parser, rules engine, and report builder — no network or API key needed."""
from __future__ import annotations

from datetime import datetime, timezone

from app.analysis import rule_based_analysis
from app.crawler.seo_parser import normalize_link, parse_page
from app.report import render_html
from app.schemas import AuditResult, AuditStatus, CrawlResult

SAMPLE_HTML = """
<html lang="en">
<head>
  <title>Acme Widgets — Best Widgets Online</title>
  <meta name="description" content="Buy the best widgets online with fast shipping and great support." />
  <link rel="canonical" href="https://acme.test/" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta property="og:title" content="Acme Widgets" />
  <script type="application/ld+json">{"@type":"Organization"}</script>
</head>
<body>
  <h1>Welcome to Acme</h1>
  <h2>Our widgets</h2>
  <img src="a.png" alt="A widget" />
  <img src="b.png" />
  <a href="/about">About</a>
  <a href="https://external.test/page">External</a>
  <p>{words}</p>
</body>
</html>
""".replace("{words}", " ".join(["widget"] * 400))


def test_normalize_link():
    assert normalize_link("https://acme.test/", "/about") == "https://acme.test/about"
    assert normalize_link("https://acme.test/", "mailto:x@y.com") is None
    assert normalize_link("https://acme.test/", "#section") is None
    assert normalize_link("https://acme.test/x", "https://o.com/p#frag") == "https://o.com/p"


def test_parse_page_extracts_signals():
    page, links = parse_page("https://acme.test/", SAMPLE_HTML, 200, 120, "acme.test")
    assert page.title == "Acme Widgets — Best Widgets Online"
    assert page.meta_description_length > 0
    assert page.h1 == ["Welcome to Acme"]
    assert page.h2_count == 1
    assert page.canonical == "https://acme.test/"
    assert page.has_viewport and page.has_open_graph and page.has_schema
    assert page.images_total == 2 and page.images_missing_alt == 1
    assert page.internal_links == 1 and page.external_links == 1
    assert page.word_count >= 400
    assert "https://acme.test/about" in links


def test_rules_flag_missing_title_and_alt():
    bad_html = "<html><body><img src='x.png'><p>short</p></body></html>"
    page, _ = parse_page("https://acme.test/bad", bad_html, 200, 50, "acme.test")
    crawl = CrawlResult(start_url="https://acme.test/bad", domain="acme.test",
                        pages=[page], crawled_at=datetime.now(timezone.utc))
    analysis = rule_based_analysis(crawl)
    titles = [i.title for i in analysis.issues]
    assert "Missing page titles" in titles
    assert "Missing meta descriptions" in titles
    assert "Missing H1 heading" in titles
    assert 0 <= analysis.score <= 100


def test_report_renders_html():
    page, _ = parse_page("https://acme.test/", SAMPLE_HTML, 200, 120, "acme.test")
    crawl = CrawlResult(start_url="https://acme.test/", domain="acme.test",
                        pages=[page], links_checked=2, crawled_at=datetime.now(timezone.utc))
    analysis = rule_based_analysis(crawl)
    audit = AuditResult(id="test123", url="https://acme.test/", status=AuditStatus.done,
                        created_at=datetime.now(timezone.utc), crawl=crawl, analysis=analysis,
                        score=analysis.score)
    html = render_html(audit)
    assert "SEO Audit Report" in html
    assert "acme.test" in html
    assert "Executive summary" in html
