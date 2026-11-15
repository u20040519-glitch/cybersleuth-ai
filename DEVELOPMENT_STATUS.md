# CYBERSLEUTH AI - Development Status

**Project:** CyberSleuth AI — Multimodal AI-Powered Digital Forensics & Evidence Reconstruction Platform  
**Version:** 1.0.0 (All 7 phases complete)  
**Status:** Phases 1–7 implemented and verified end-to-end  
**Last updated:** 2026-11-15

---

## Phase status

| Phase | Scope | Status |
| --- | --- | --- |
| **1** | Foundation & UI (React/TypeScript/Vite/Tailwind, design system, 16 pages) | ✅ **Complete** |
| **2** | Supabase-compatible schema, auth, RLS, storage, CRUD | ✅ **Complete** (local embedded PG locally; Supabase-ready migrations) |
| **3** | Evidence integrity — upload validation, SHA-256, chain of custody | ✅ **Complete** |
| **4** | Forensic modules — OpenCV / Androguard / Librosa / spaCy + NetworkX-style correlation graph | ✅ **Complete** |
| **5** | AI correlation — timeline, graph, Gemini explanation layer | ✅ **Complete** |
| **6** | Reports — PDF generation | ✅ **Complete** |
| **7** | Testing, security hardening, deployment | ✅ **Complete** |

---

## What was done in Phases 2–7 (this round)

### Phase 2 — Data & access layer
- 12 SQL migrations in `supabase/migrations/` as the single source of truth (embedded PG locally, `supabase db push` in cloud).
- Restricted application role `cybersleuth_app`; **RLS enabled on all tables** and genuinely enforced by connecting as that non-superuser.
- **Fixed**: nested `$$` dollar-quote syntax error in `000_auth_parity.sql` (broke all bootstraps).
- **Fixed**: migrations crashed on `pgcrypto`/`uuid-ossp` unavailable on the embedded server (now best-effort; schema only needs `gen_random_uuid()`).
- **Fixed**: `can_access_investigation` re-read the very row being inserted, so `INSERT ... RETURNING` always failed RLS on the brand-new investigations row — fixed with a direct column comparison policy (`owner_id = current_user_id()`) and a shared `is_investigation_member()` helper (migration `011`).
- **Fixed**: SQLAlchemy model mapped `metadata_json` onto a non-existent column (real column is `metadata`) — mapped explicitly for `evidence` and `generated_reports`.
- **Fixed**: `auth.users` double-qualified as `auth."auth.users"` — mapped to schema `auth`, table `users`.
- Storage: local filesystem backend at `backend/storage/` with immutable `evidence-originals`, `evidence-derived`, `reports` buckets; SupabaseStorageBackend implemented and keyed correctly (double bucket-prefix bug fixed).
- **Deployment**: `bootstrap_database()` now honours `DATABASE_URL` (migrations) and a new `APP_DATABASE_URL` (runtime, restricted role); local dev unchanged (embedded PG).

### Phase 3 — Evidence integrity
- Upload pipeline: stream to temp → validate (allow-list MIME/extension, size cap 100 MB) → SHA-256 → **re-hash after storage and compare** → immutable original row → custody event.
- `/evidence/{id}/integrity-check` re-verifies on demand; `/custody/verify` replays the hash chain; custody ledger is append-only (DB trigger + revoked grants + test).
- **Fixed**: `storage_path=''` placeholder INSERT then UPDATE broke the immutable-original trigger — the file is now stored under a random key *before* the row exists (no UPDATE ever happens).
- Audit events written for register/login/logout/upload/analyze/correlate/generate/download.

### Phase 4 — Forensic modules
- **DeepTrace AI** (existing, 57 KB, real): EXIF review, Error Level Analysis, noise residuals, copy-move detection, block-grid and geometry checks, EXIF timeline events. Reads the file, never writes it.
- **VoiceProof AI** (existing, 34 KB, real): Librosa load, non-silent segments, silence map, splice-seam regularity heuristics, level statistics. Segment events are anchored to the file's mtime (not 1970).
- **SpyTrace AI** (built this round, real): Androguard 4.1.3 static analysis — package identity, signing scheme + X.509 certificate extraction (subject/issuer/validity/self-signed), 20 weighted stalkerware permissions with risk bands, accessibility-service and boot-persistence heuristics, exported component surface from the manifest XML, embedded URLs/IPs/emails from DEX string tables.
- **CyberSleuth AI** (built this round, real): UTF-8/UTF-16/latin-1 decoding, JSON-chat/CSV/WhatsApp/text structure detection, ISO/EU/WhatsApp timestamp parsing, regex entities (emails, URLs, IPs, phones, SHA-256), spaCy `en_core_web_sm` NER (PERSON/ORG/GPE/LOC/DATE/TIME/EVENT/NORP), timeline events with inline entity tags.

### Phase 5 — Correlation & AI explanation
- Correlation engine now: attaches each artefact's **own SHA-256 as an entity** to its events, flattens **undated findings** for entity detection (kept out of the displayed timeline), and dedupes connections per (evidence₁, evidence₂, entity).
- Gemini explanation layer runs **only when connections exist**, receives strictly structured findings, and degrades to `{available: false, reason}` on failure. Model updated `gemini-1.5-flash → gemini-2.5-flash → gemini-3.5-flash` (deprecated IDs removed by Google).
- Relationship graph returned with evidence/event nodes and weighted edges; the UI renders a real SVG graph (not a placeholder).
- Frontend Correlation page: investigation picker, POST run + GET latest run, timeline, connections, graph, Gemini explanation, honest investigator-review disclaimer.

### Phase 6 — PDF reports
- **Fixed**: `_para` now accepts a pre-built `ParagraphStyle` (was `STYLES[...]` on an object → crash).
- **Fixed**: ReportLab `TableStyle` colour/width argument order (`LINEBELOW`/`LINEBEFORE`) — "Unknown color 1.5".
- **Fixed**: upload-time metadata (e.g. an APK's 200-entry ZIP listing) could exceed page height — metadata values are coerced and truncated to 300 chars.
- Report flow verified end-to-end: render → store under `reports/` → SHA-256 → download with auth + `X-Report-SHA256` header; a **10-page PDF** generated from the seeded case.

### Phase 7 — Tests, security, deployment
- **41 pytest tests**, all passing, against an isolated `cybersleuth_test` database (rebuilt per session, truncated per test, `NullPool` for cross-loop asyncpg safety):
  - `test_auth.py` — register/login/me/refresh/logout, Argon2 verify, duplicate 409, wrong password 401, **429 rate limit after burst**
  - `test_investigations.py` — CRUD, **409 on duplicate case_id** (was 500), RLS-scoped access, supervisor non-member 404
  - `test_evidence.py` — upload + SHA-256 match, integrity-check, custody verify, 400 on disallowed extension, 401 unauthenticated, scoped listing, authenticated download bytes + header
  - `test_forensics.py` — DeepTrace on real JPEG, CyberSleuth on chat JSON (structure/regex/timeline counts), correlation unit tests (hash-entity attachment, shared-entity links, timestamp match), 404 on inaccessible evidence
  - `test_reports.py` — generate → `ready` → download `%PDF` bytes + SHA-256 header; list scoped to investigation
  - `test_health.py` — health payload, security headers, 404
- **Security hardening**: per-IP rate limiting on `/auth/login` (10/min) and `/auth/register` (5/min); security headers middleware (`nosniff`, `DENY`, `no-referrer`, `Permissions-Policy`, HSTS in production); refresh token now re-reads the profile **under RLS** (was returning 401 for every refresh); audit/custody append-only enforcement unchanged and now test-covered.
- **Deployment**: backend `Dockerfile` (multi-stage, root build context, non-root user, healthcheck), `.dockerignore`, `render.yaml` blueprint (health check `/api/health`), Netlify config maintained, root `vite.config.ts` proxy target pinned to `127.0.0.1` (IPv6 `localhost` hang fixed).
- Frontend: **all demo fallbacks removed** — real auth (JWT + refresh), live dashboard (recharts from DB), live investigations/evidence/audit views, real module pages (investigation → evidence picker → run → results), correlation UI with graph, reports with generate/download, **zero console/page errors** in Chromium.
- Seeding: `scripts/seed_demo_data.py` reproduces the full demo from the live API idempotently.

---

## Verification evidence (this session)

| Check | Result |
| --- | --- |
| `pytest -q` (backend) | **41 passed** |
| `npx tsc --noEmit` (frontend) | **0 errors** |
| `npm run build` (frontend) | ✅ built (783 kB JS / 228 kB gzip) |
| Browser smoke (Chromium, 23 checks) | **ALL PASSED** — login → dashboard → investigations → evidence → DeepTrace run → reports → audit logs; **0 console errors, 0 page errors** |
| Seeded case — Operation Silent Whisper | 2 cases · 6 evidence files · 7 module runs · 4–5 correlations (shared APK↔chat URL, shared sha256, timestamp matches) · 10-page PDF |
| Gemini explanation | `available: true`, grounded in findings (model `gemini-3.5-flash`) |
| PDF report download | 200, `%PDF` magic, `X-Report-SHA256` matches DB row |
| RLS | Enforced by non-superuser `cybersleuth_app`; `INSERT ... RETURNING` fixed via migration 011 |
| Browser console sweep | 0 errors on every visited route |

---

## How to run

```bash
# backend (first run creates embedded PG, applies migrations, seeds app role)
cd backend && ..\.venv310\Scripts\python.exe -m uvicorn app.main:app --port 8000

# frontend
cd frontend && npm run dev          # http://localhost:3000

# tests
cd backend && ..\.venv310\Scripts\python.exe -m pytest -q

# reseed (idempotent — safe to re-run)
python scripts/seed_demo_data.py
```

Seeded sign-ins: `investigator@cybersleuth.ai / Investigator!2026` and `supervisor@cybersleuth.ai / Supervisor!2026` (**rotate in production**).

---

## Known limitations (honest)

1. No calibrated forensic models are bundled; findings are labelled `measured`/`heuristic` and `confidence_score` stays `null` — nothing is presented as a verdict.
2. Rate limiting is in-memory per process (use Redis for multi-replica).
3. The embedded PG is for development; production should use managed Postgres via `DATABASE_URL`/`APP_DATABASE_URL` (see `render.yaml`).
4. Gemini explanation requires `GEMINI_API_KEY`; without it the correlation still runs and reports `available: false` with a reason.
5. The seeded demo accounts must be removed or rotated in any real deployment; the default local DB password is development-only.
6. ReportLab tables truncate upload-time metadata cell values to 300 chars to stay within page bounds.
