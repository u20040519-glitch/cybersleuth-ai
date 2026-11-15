# CyberSleuth AI - Backend

> FastAPI service for the CyberSleuth AI digital forensics platform.
> **Status: implemented and verified — see `../DEVELOPMENT_STATUS.md`.**

The backend was rebuilt for CyberSleuth AI. The previous implementation in this
repository belonged to a different project (PROJECT NEXUS AI) and has been removed.
That code remains available in the git history if it is ever needed.

---

## Structure

```
backend/
├── app/
│   ├── main.py               FastAPI app, middleware, router mounting, security headers
│   ├── core/                 config, security primitives (Argon2id, JWT, SHA-256),
│   │                         rate limiting
│   ├── schemas/              Pydantic request/response models
│   ├── models/               SQLAlchemy models (mirrors supabase/migrations)
│   ├── api/                  routers: auth, investigations, evidence, deeptrace,
│   │                         spytrace, voiceproof, cybersleuth, correlation,
│   │                         reports, audit, dashboard, health
│   ├── services/             storage (local FS / Supabase), evidence validation,
│   │                         custody ledger, audit writer, Gemini client
│   ├── security/             Bearer-token resolution, RBAC, RLS identity publication
│   ├── database/             embedded-PG bootstrap, migration runner, RLS provisioning
│   ├── forensic/
│   │   ├── deeptrace/        OpenCV + Pillow: EXIF, ELA, noise, copy-move, grid, geometry
│   │   ├── spytrace/         Androguard 4.x: manifest, permissions, cert, strings, risk band
│   │   ├── voiceproof/       Librosa: segments, silence map, splice seams, levels
│   │   └── cybersleuth/      spaCy NER + regex + JSON/CSV/WhatsApp structure, timeline
│   ├── correlation/          entity normalisation, timeline builder, graph builder
│   └── reports/              reportlab PDF renderer
├── tests/                    41-test pytest suite (runs against cybersleuth_test DB)
└── requirements.txt
```

## Local setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
copy .env.example .env      # then put your own values in
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

On first start the API creates an embedded PostgreSQL under `backend/.pgdata`,
applies every migration in `../supabase/migrations/`, and provisions the restricted
`cybersleuth_app` role. No Supabase account or DSN is required for local development.

API docs: <http://127.0.0.1:8000/docs>

## Environment variables

**Backend only — never expose any of these to the frontend.** A `VITE_` prefix would
inline them into the browser bundle.

See [`.env.example`](.env.example) for the full list. Key ones:

| Variable | Purpose |
|---|---|
| `APP_SECRET_KEY` | Session signing key, ≥ 32 chars (HS256) |
| `DATABASE_URL` | Privileged URL for migrations only (e.g. Supabase Postgres). Unset locally → embedded server. |
| `APP_DATABASE_URL` | Restricted runtime role used by the API (unset locally → auto-provisioned) |
| `APP_DB_USER` / `APP_DB_PASSWORD` | Restricted role name/password provisioned by migrations |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Optional Supabase project (storage + auth path) |
| `STORAGE_BACKEND` | `local` (default, filesystem) or `supabase` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Explanation layer (backend only) |
| `MAX_UPLOAD_SIZE_MB` | Upload cap (default 100) |
| `ALLOWED_EXTENSIONS` | Evidence file-type allowlist |
| `CORS_ORIGINS` | Comma-separated allowed origins for the frontend |

## Design rules that hold

1. **Never execute an uploaded file.** APK analysis is static only.
2. **Never modify an original.** Processed artefacts are written to separate paths;
   the database refuses updates to hash/size/path/filename.
3. **Never fabricate a forensic finding.** If a module cannot run, it returns
   `status: "unavailable"` with a reason.
4. **Never trust the client.** Authorisation is enforced server-side on every
   resource and again by PostgreSQL RLS.
5. **Never let Gemini be the detection mechanism.** It explains structured findings;
   it does not create them.
6. **Never log secrets** or raw evidence contents.
