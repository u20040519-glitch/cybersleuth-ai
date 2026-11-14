# CyberSleuth AI — Backend

> FastAPI service for the CyberSleuth AI digital forensics platform.
> **Status: not yet implemented — this is the Phase 2 target structure.**

The backend was rebuilt for CyberSleuth AI. The previous implementation in this
repository belonged to a different project (PROJECT NEXUS AI) and has been removed.
That code remains available in the git history if it is ever needed.

---

## Planned structure (Phase 2+)

```
backend/
├── app/
│   ├── main.py               FastAPI app factory, middleware, router mounting
│   ├── core/                 config, security primitives, logging, exceptions
│   ├── schemas/              Pydantic request/response models
│   ├── models/               database model definitions
│   ├── api/                  routers: investigations, evidence, deeptrace,
│   │                         spytrace, voiceproof, cybersleuth, correlation,
│   │                         reports, audit, auth, health
│   ├── services/             storage, hashing, gemini client, job dispatcher,
│   │                         audit writer
│   ├── security/             Supabase JWT verification, RBAC, case access
│   ├── database/             Supabase client factory, repositories
│   ├── forensic/
│   │   ├── deeptrace/        OpenCV metadata + frame extraction + ELA checks
│   │   ├── spytrace/         Androguard APK static analysis
│   │   ├── voiceproof/       Librosa waveform + spectrogram + anomaly detection
│   │   └── cybersleuth/      timestamp/entity extraction, spaCy, NetworkX graph
│   ├── correlation/          entity normalisation, timeline builder, graph builder
│   └── reports/              PDF renderer
├── tests/                    pytest suite
└── requirements.txt
```

---

## Local setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then add SUPABASE_* and GEMINI_API_KEY locally
uvicorn app.main:app --reload
```

API docs: <http://localhost:8000/docs>

---

## Environment variables

**Backend only — never expose any of these to the frontend.** A `VITE_` prefix would
inline them into the browser bundle.

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role key — **bypasses RLS**, so the backend must re-verify authorisation itself |
| `GEMINI_API_KEY` | Gemini API key for the explanation layer only |
| `GEMINI_MODEL` | Model name, configurable rather than hardcoded |
| `FRONTEND_URL` | Allowed CORS origin (your Netlify URL) |
| `MAX_UPLOAD_SIZE_MB` | Upload size cap |
| `ALLOWED_EXTENSIONS` | Evidence file-type allowlist |

See `../.env.example` for the full template and `../docs/SECURITY.md` for the rules.

---

## Design rules that must hold

1. **Never execute an uploaded file.** APK analysis is static only.
2. **Never modify an original.** Processed artefacts are written to a separate path.
3. **Never fabricate a forensic finding.** If no calibrated model is configured, return
   `status: "unavailable"` with a reason.
4. **Never trust the client.** Authorisation is enforced server-side on every resource.
5. **Never let Gemini be the detection mechanism.** It explains structured findings; it
   does not create them.
6. **Never log secrets** or raw evidence contents.

---

**Next step →** Phase 2. See `../DEVELOPMENT_STATUS.md` for the full task list.
