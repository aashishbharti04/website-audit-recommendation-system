"""Phase 5 — optional PostgreSQL persistence for audit history per client domain.

This is scaffolding: the SQLAlchemy model and helpers are here and wired to `DATABASE_URL`,
but the audit service currently uses the in-memory `AUDITS` store. To enable history:

1. Set DATABASE_URL in .env (e.g. a Supabase/Railway Postgres connection string).
2. Call `init_db()` on startup (e.g. a FastAPI lifespan handler).
3. In `audit/service.run_audit`, persist the finished AuditResult via `save_audit()`.

Kept intentionally small — extend with auth/users and a `clients` table as the agency grows.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from .config import get_settings

try:
    from sqlalchemy import JSON, DateTime, Integer, String, Text, create_engine, select
    from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
    _SQLALCHEMY = True
except Exception:  # SQLAlchemy not installed
    _SQLALCHEMY = False


if _SQLALCHEMY:

    class Base(DeclarativeBase):
        pass

    class AuditRecord(Base):
        __tablename__ = "audits"

        id: Mapped[str] = mapped_column(String(32), primary_key=True)
        domain: Mapped[str] = mapped_column(String(255), index=True)
        url: Mapped[str] = mapped_column(Text)
        client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
        score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
        status: Mapped[str] = mapped_column(String(32))
        result_json: Mapped[dict] = mapped_column(JSON)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    _engine = None

    def _get_engine():
        global _engine
        cfg = get_settings()
        if not cfg.database_url:
            raise RuntimeError("DATABASE_URL is not configured.")
        if _engine is None:
            _engine = create_engine(cfg.database_url, pool_pre_ping=True)
        return _engine

    def init_db() -> None:
        Base.metadata.create_all(_get_engine())

    def save_audit(audit) -> None:
        """Persist a finished AuditResult (Pydantic model)."""
        with Session(_get_engine()) as session:
            rec = AuditRecord(
                id=audit.id,
                domain=audit.crawl.domain if audit.crawl else "",
                url=audit.url,
                client_name=audit.client_name,
                score=audit.score,
                status=audit.status.value,
                result_json=json.loads(audit.model_dump_json()),
                created_at=audit.created_at or datetime.now(timezone.utc),
            )
            session.merge(rec)
            session.commit()

    def history_for_domain(domain: str, limit: int = 50) -> list[dict]:
        with Session(_get_engine()) as session:
            rows = session.execute(
                select(AuditRecord).where(AuditRecord.domain == domain)
                .order_by(AuditRecord.created_at.desc()).limit(limit)
            ).scalars().all()
            return [{"id": r.id, "score": r.score, "created_at": r.created_at.isoformat()} for r in rows]

else:
    def init_db() -> None:
        raise RuntimeError("SQLAlchemy is not installed; persistence is unavailable.")

    def save_audit(audit) -> None:  # noqa: D401
        raise RuntimeError("SQLAlchemy is not installed; persistence is unavailable.")

    def history_for_domain(domain: str, limit: int = 50) -> list[dict]:
        raise RuntimeError("SQLAlchemy is not installed; persistence is unavailable.")
