"""Extract on-page SEO signals from a fetched HTML document with BeautifulSoup."""
from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from ..schemas import PageSEO


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def normalize_link(base_url: str, href: str) -> str | None:
    """Resolve a href to an absolute http(s) URL, stripping fragments."""
    if not href:
        return None
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
        return None
    absolute = urljoin(base_url, href)
    absolute, _ = urldefrag(absolute)
    if not absolute.startswith(("http://", "https://")):
        return None
    return absolute


def parse_page(url: str, html: str, status: int | None, load_ms: int | None, base_domain: str) -> tuple[PageSEO, set[str]]:
    """Return the page's SEO snapshot and the set of absolute links found on it."""
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.title.string.strip() if soup.title and soup.title.string else None

    def meta(name: str, attr: str = "name") -> str | None:
        tag = soup.find("meta", attrs={attr: name})
        return tag.get("content", "").strip() if tag and tag.get("content") else None

    meta_desc = meta("description")
    h1 = [h.get_text(strip=True) for h in soup.find_all("h1")]
    canonical_tag = soup.find("link", rel="canonical")
    canonical = canonical_tag.get("href") if canonical_tag else None

    images = soup.find_all("img")
    missing_alt = sum(1 for img in images if not img.get("alt", "").strip())

    body_text = soup.get_text(" ", strip=True)
    word_count = len(body_text.split())

    internal, external = 0, 0
    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        absolute = normalize_link(url, a["href"])
        if not absolute:
            continue
        links.add(absolute)
        if _domain(absolute) == base_domain:
            internal += 1
        else:
            external += 1

    has_schema = bool(
        soup.find("script", attrs={"type": "application/ld+json"})
        or soup.find(attrs={"itemtype": True})
    )

    page = PageSEO(
        url=url,
        status=status,
        title=title_tag,
        title_length=len(title_tag) if title_tag else 0,
        meta_description=meta_desc,
        meta_description_length=len(meta_desc) if meta_desc else 0,
        h1=h1,
        h2_count=len(soup.find_all("h2")),
        canonical=canonical,
        robots_meta=meta("robots"),
        word_count=word_count,
        images_total=len(images),
        images_missing_alt=missing_alt,
        has_viewport=bool(soup.find("meta", attrs={"name": "viewport"})),
        has_open_graph=bool(soup.find("meta", attrs={"property": "og:title"})),
        has_schema=has_schema,
        lang=(soup.html.get("lang") if soup.html else None),
        internal_links=internal,
        external_links=external,
        load_ms=load_ms,
    )
    return page, links
