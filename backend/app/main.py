"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .report import weasyprint_available
from .routes import audits, ws

cfg = get_settings()

app = FastAPI(
    title="SeoTuners SEO Audit API",
    version=__version__,
    description="White-label SEO audit engine: crawl, analyse, and generate branded reports.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audits.router)
app.include_router(ws.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "ai_enabled": cfg.ai_enabled,
        "ai_model": cfg.ai_model if cfg.ai_enabled else None,
        "pdf_enabled": weasyprint_available(),
        "agency": cfg.agency_name,
    }
