# 🔍 SeoTuners — White-Label SEO Audit SaaS

An internal, white-label SEO audit tool for the agency: enter a client URL, it crawls the
site, runs deterministic SEO checks **and** an AI analysis, and produces a branded,
prioritised report (HTML + PDF) your team can hand to clients.

> **Private / internal.** This repository contains agency branding and is not open source.

---

## Architecture

```
Frontend (React / Vite)         Backend (FastAPI / Python)              AI + data
┌───────────────────────┐  REST ┌────────────────────────────┐  API ┌─────────────────────┐
│ URL input + options   │ ─────▶│ Crawler   (httpx + BS4)     │ ────▶│ Claude API          │
│ Live progress (WS)    │  WS   │ Link checker (aiohttp)      │      │  (claude-sonnet-4-6)│
│ Report viewer         │ ◀──── │ Rules engine (deterministic)│      │ PostgreSQL (history)│
│ Export PDF / HTML     │       │ AI analyst (structured out) │      │  (optional, Phase 5)│
└───────────────────────┘       │ Report builder (WeasyPrint) │      └─────────────────────┘
                                └────────────────────────────┘
```

## What's built (all 5 phases scaffolded)

| Phase | Area | Status |
|------|------|--------|
| **1** | **Crawler** — async BFS crawl (`httpx`), on-page SEO extraction (`BeautifulSoup`), async link checker (`aiohttp`) | ✅ working |
| **2** | **AI analysis** — real crawl data → Claude via **structured outputs** (`messages.parse` + Pydantic), with a graceful fallback to the rules engine if no key | ✅ working |
| **3** | **Report builder** — branded HTML (Jinja2) + PDF (WeasyPrint), shared template, white-label config | ✅ working (PDF needs native libs) |
| **4** | **React dashboard** — URL form → live WebSocket progress → filterable report → HTML/PDF export | ✅ working |
| **5** | **History & persistence** — SQLAlchemy model + Postgres wiring for per-domain audit history | 🟡 scaffolded (in-memory store active; flip to DB via `db.py`) |

A **deterministic rules engine** (`analysis/rules.py`) runs on every audit, so the tool is
useful even before you add a Claude key — and it gives the AI verified findings to expand on
rather than invent.

## Quick start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY for AI analysis (optional)
uvicorn app.main:app --reload
```

API now at `http://localhost:8000` (`/api/health`, interactive docs at `/docs`).

> **PDF export** needs WeasyPrint's native libraries (pango/cairo). They're baked into the
> backend `Dockerfile`; for local installs see the
> [WeasyPrint install guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).
> Without them, HTML export still works and the API returns a clear 501 for PDF.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api + /ws to :8000)
```

### Docker (API + Postgres)

```bash
ANTHROPIC_API_KEY=sk-... docker compose up --build
```

## How it works

1. `POST /api/audits` `{ url, options }` → returns an audit `id`, starts a background job.
2. The dashboard opens `ws://…/ws/audits/{id}` and streams **live progress** (crawl → links → analysis).
3. The job: crawl → check links → **rules engine** → **Claude analysis** → assemble result.
4. `GET /api/audits/{id}` returns the full result; `…/report.html` and `…/report.pdf` export it.

## Configuration

All via env (`backend/.env` — see `.env.example`). Highlights:

| Var | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Enables AI analysis. Without it, the rules engine is used. |
| `AI_MODEL` | `claude-sonnet-4-6` (default, best cost/speed for this volume) or `claude-opus-4-8`. |
| `AGENCY_NAME` / `AGENCY_LOGO_URL` / `AGENCY_PRIMARY_COLOR` / … | White-label branding on every report. |
| `DATABASE_URL` | Postgres for audit history (Phase 5). |

## Tech stack

| Layer | Tool |
|---|---|
| Backend | Python · FastAPI · httpx · BeautifulSoup · aiohttp |
| AI | Anthropic SDK (`claude-sonnet-4-6`), structured outputs |
| Reports | Jinja2 + WeasyPrint |
| Frontend | React + Vite |
| DB | PostgreSQL (SQLAlchemy) — optional |
| Deploy | Docker / Railway / Render |

## Cost to run

- Claude API: ~$0.10–0.30 per audit (Sonnet 4.6, depends on site size)
- Hosting: ~$5–10/mo (Railway/Render) · Postgres free tier to start
- **Under ~$20/mo at agency scale.**

## Tests

```bash
cd backend && python -m pytest -q     # parser, rules engine, report builder (no network/key)
```

## Roadmap

- [ ] Wire `db.py` persistence into the audit service + a history view per client domain
- [ ] Agency login / multi-user auth (Phase 5)
- [ ] Optional DataForSEO integration for real SERP positions & keyword rankings
- [ ] Scheduled re-audits + score-trend charts
- [ ] PageSpeed Insights / Core Web Vitals enrichment

---

© SeoTuners — internal tool. Confidential.
