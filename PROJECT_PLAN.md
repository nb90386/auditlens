# Project 2: Autonomous QA / UX Auditor — "AuditLens"

## One-Sentence Pitch
A web app that crawls any URL, runs automated checks for responsiveness, accessibility, performance, and UI issues, then generates a beautiful scored audit report with AI-suggested fixes.

## Target User
- Frontend developers who want quick QA reports
- Freelance web designers showing clients professional audits
- Small business owners checking their own site quality

## Core Problem
Running Lighthouse, aXe, and manual QA checks separately is tedious. AuditLens combines everything into one click.

## Key Features
1. **URL Crawl & Audit** — Enter a URL, get a full audit in ~30 seconds
2. **Scoring Dashboard** — Overall score + category scores (a11y, performance, SEO, best practices)
3. **Screenshot Capture** — Desktop + mobile viewport screenshots
4. **Issue Cards** — Each issue with severity, description, and suggested fix
5. **AI Improvement Plan** — Prioritized list of fixes (mock AI if no API key)
6. **Report History** — Past audits stored and comparable
7. **Export** — JSON export of full report
8. **Responsive Check** — Simulated viewport testing

## Tech Stack
- **Backend**: Python + FastAPI + SQLite
- **Frontend**: Vanilla JS + CSS (dark theme, glass morphism)
- **Scoring**: Custom heuristic engine (no external API needed for demo)
- **Screenshots**: Placeholder with realistic audit data
- **Tests**: pytest for API, Playwright-style assertions

## Architecture
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser    │────▶│  FastAPI     │────▶│   SQLite    │
│   (JS SPA)   │◀────│  Backend     │◀────│   Database  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │ Audit Engine │
                    │ (heuristics) │
                    └─────────────┘
```

## Data Model
- **audits**: id, url, status, overall_score, created_at
- **audit_scores**: id, audit_id, category, score, max_score
- **audit_issues**: id, audit_id, severity, category, title, description, suggestion, element

## API Routes
- `POST /api/audits` — Start new audit
- `GET /api/audits` — List all audits
- `GET /api/audits/{id}` — Get full audit with scores + issues
- `GET /api/audits/{id}/report` — Get formatted report
- `DELETE /api/audits/{id}` — Delete audit

## UI Screens
1. Landing: URL input + "Run Audit" button
2. Loading: Animated scanning progress
3. Dashboard: Score rings, category breakdown, issue list
4. Report Detail: Full issue cards with fixes
5. History: Past audits table

## Testing Plan
- Unit: Audit engine scoring logic
- API: All CRUD endpoints
- Integration: Full audit flow

## Deployment
- Cloudflare Worker (single HTML + API routes)
- Or Render/Railway for full backend

## Definition of Done
- [ ] Backend API with all routes
- [ ] Audit engine with realistic scoring
- [ ] Frontend with all screens
- [ ] Tests passing
- [ ] README with screenshots
- [ ] CI workflow
- [ ] Deployed live
