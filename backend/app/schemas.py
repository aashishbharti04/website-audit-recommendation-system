"""Pydantic models shared across the backend (crawl data, AI analysis, audit results)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------- request ----------
class AuditOptions(BaseModel):
    max_pages: int = Field(20, ge=1, le=200, description="How many pages to crawl.")
    check_links: bool = True
    use_ai: bool = True
    client_name: Optional[str] = None  # appears on the report


class AuditRequest(BaseModel):
    url: str
    options: AuditOptions = AuditOptions()


# ---------- crawl ----------
class LinkStatus(BaseModel):
    url: str
    status: Optional[int] = None
    ok: bool = False
    internal: bool = True
    error: Optional[str] = None


class PageSEO(BaseModel):
    url: str
    status: Optional[int] = None
    title: Optional[str] = None
    title_length: int = 0
    meta_description: Optional[str] = None
    meta_description_length: int = 0
    h1: list[str] = []
    h2_count: int = 0
    canonical: Optional[str] = None
    robots_meta: Optional[str] = None
    word_count: int = 0
    images_total: int = 0
    images_missing_alt: int = 0
    has_viewport: bool = False
    has_open_graph: bool = False
    has_schema: bool = False
    lang: Optional[str] = None
    internal_links: int = 0
    external_links: int = 0
    load_ms: Optional[int] = None
    error: Optional[str] = None


class CrawlResult(BaseModel):
    start_url: str
    domain: str
    pages: list[PageSEO] = []
    broken_links: list[LinkStatus] = []
    links_checked: int = 0
    crawled_at: datetime


# ---------- analysis ----------
class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Category(str, Enum):
    on_page = "On-Page"
    technical = "Technical"
    content = "Content"
    links = "Links"
    performance = "Performance"
    mobile = "Mobile"
    structured_data = "Structured Data"


class Issue(BaseModel):
    title: str
    category: Category
    severity: Severity
    description: str
    recommendation: str
    affected: Optional[str] = Field(None, description="Pages or elements affected, if specific.")


class AIAnalysis(BaseModel):
    """The schema Claude is forced to fill (structured outputs)."""
    executive_summary: str = Field(..., description="2-4 sentence plain-English overview for the client.")
    score: int = Field(..., ge=0, le=100, description="Overall SEO health score 0-100.")
    issues: list[Issue] = Field(..., description="Prioritised issues, most severe first.")
    quick_wins: list[str] = Field(default_factory=list, description="3-5 highest-impact actions to do first.")


# ---------- audit job ----------
class AuditStatus(str, Enum):
    queued = "queued"
    crawling = "crawling"
    checking_links = "checking_links"
    analyzing = "analyzing"
    building_report = "building_report"
    done = "done"
    error = "error"


class ProgressEvent(BaseModel):
    status: AuditStatus
    message: str
    pct: int = 0


class AuditResult(BaseModel):
    id: str
    url: str
    client_name: Optional[str] = None
    status: AuditStatus
    created_at: datetime
    crawl: Optional[CrawlResult] = None
    analysis: Optional[AIAnalysis] = None
    score: Optional[int] = None
    error: Optional[str] = None
