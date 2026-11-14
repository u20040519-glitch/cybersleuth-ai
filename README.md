# 🔍 CyberSleuth AI

> **Multimodal AI-Powered Digital Forensics & Evidence Reconstruction Platform**
>
> *Detect the Threat. Decode the Evidence. Reconstruct the Truth.*

CyberSleuth AI is a unified digital forensics platform for investigators to **upload, securely store, analyse, correlate, and report** digital evidence from multiple sources — images, video, audio, Android packages, and structured data artefacts.

Four specialist forensic modules work inside **one shared investigation system**, connected by a central AI-powered correlation engine.

| Module | Purpose |
|---|---|
| **DeepTrace AI** | Image & video forensics — metadata, frame extraction, manipulation checks |
| **SpyTrace AI** | Android spyware & mobile artefact analysis — APK static analysis, permissions, components |
| **VoiceProof AI** | Audio & synthetic voice forensics — waveform, spectrogram, anomaly detection |
| **CyberSleuth AI** | Digital evidence extraction — timestamps, entities, timeline, relationship graph |

---

## 📌 Project Status

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | Foundation & UI (frontend, design system, navigation, all pages) | ✅ **Complete** |
| Phase 2 | Supabase — schema, auth, RLS, storage, CRUD | ⬜ Not started |
| Phase 3 | Evidence integrity — validation, SHA-256, chain of custody | ⬜ Not started |
| Phase 4 | Forensic modules — OpenCV / Androguard / Librosa / spaCy | ⬜ Not started |
| Phase 5 | AI correlation — timeline, graph, Gemini explanation layer | ⬜ Not started |
| Phase 6 | Reports — PDF generation | ⬜ Not started |
| Phase 7 | Testing, security, deployment | ⬜ Not started |

> **Current build is a complete, navigable frontend.** Backend calls are wired to a
> prepared Axios service layer and will activate when the Phase 2 backend is running.
> Pages that need live data show an honest **"Demo mode"** empty state rather than
> fabricated forensic findings.

See [`DEVELOPMENT_STATUS.md`](./DEVELOPMENT_STATUS.md) for the detailed breakdown.

---

## 🎯 Problem Statement

Digital investigations today are fragmented across single-purpose tools: one app for
image forensics, another for APK inspection, another for audio, another for log parsing.
Evidence lives in scattered folders, and correlating a suspicious video with a chat
export or an APK requires manual cross-referencing in spreadsheets.

This fragmentation causes three concrete failures:

1. **No unified timeline** — findings from different tools cannot be placed on a single chronology.
2. **Broken chain of custody** — files are copied between tools, weakening evidentiary integrity.
3. **No explainable reasoning** — automated outputs are treated as conclusions rather than hypotheses.

---

## 🎯 Objectives

1. Provide **one investigation container** for all evidence and all module outputs.
2. Guarantee **evidence integrity** via SHA-256 hashing and an immutable chain-of-custody trail.
3. **Correlate findings across modalities** into a single evidence-linked timeline and relationship graph.
4. Keep **technical observations, model predictions, AI explanations, and human hypotheses clearly separated**.
5. Never present an automated result as legal proof, and never infer identity or guilt from timestamps alone.

---

## 🧩 Features

### Foundation & UI (Phase 1 — implemented)

- **Dark cyber-forensics design system** — exact palette (`#080D18` background, `#0B1220` sidebar, `#111B2B` cards, `#3B82F6` primary blue, `#22D3EE` cyan, `#E6F0FF` text), glass panels, subtle glow shadows, custom scrollbars.
- **Persistent sidebar** with all 11 navigation destinations plus a contextual top bar.
- **Responsive** layout across desktop, tablet, and mobile.
- **Protected routes** and a **guest-only** auth flow.
- **Auth screens** — sign in and registration with client-side validation.
- **Reusable component library** — Button (with `asChild`), Card, StatCard, Badge, Input, TextArea, EmptyState, LoadingSpinner.
- **Working interactions** — evidence type filter, investigation status filter, search, file selection with **client-side SHA-256 hashing**, analysis run states, report generation, logout.
- **Honest states** — every module page distinguishes *"Model not configured / analysis unavailable"* from actual findings, and labels demo content explicitly.

### Planned (Phases 2–7)

- Supabase Auth with Investigator / Supervisor roles, RLS policies, private storage buckets.
- Evidence upload with server-side validation, SHA-256 verification before and after processing, immutable chain-of-custody events, audit logging.
- Real forensic engines: OpenCV frame extraction, Androguard APK parsing, Librosa waveform/spectrogram, spaCy + NetworkX entity and graph extraction.
- Gemini explanation layer grounded strictly in structured findings.
- Professional PDF forensic reports distinguishing observations from interpretations.

---

## 🛠 Technology Stack

### Frontend
| Technology | Purpose |
|---|---|
| React 18 | UI runtime |
| TypeScript 5.5 | Type safety (strict mode) |
| Vite 5 | Dev server & build |
| Tailwind CSS 3.4 | Design system |
| shadcn/ui patterns (`@radix-ui/react-slot`) | Composable components |
| Lucide React | Iconography |
| React Router 6 | Routing & route guards |
| TanStack Query / Recharts | Data fetching & charts (installed, Phase 2 wiring) |
| Axios | HTTP client |

### Backend (Phase 2+)
Python · FastAPI · Pydantic · Uvicorn · background workers

### Data & Auth
Supabase Auth · Supabase PostgreSQL · Supabase private Storage · Row Level Security

### AI & Forensics
Google Gemini (backend only) · PyTorch · OpenCV · Librosa · scikit-learn · spaCy · NetworkX · Androguard

### Deployment
Vercel / Netlify (frontend) · Render / Railway (backend) · Supabase (database + storage) · GitHub (source)

---

## 🏗 System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Netlify)                            │
│  React + TypeScript + Vite + Tailwind   │   React Router guards      │
│  ─────────────────────────────────────────┼─────────────────────────  │
│  Dashboard │ Investigations │ Evidence   │ 4 Forensic Modules        │
│  Correlation Engine │ Reports │ Audit    │ Settings                  │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │  Axios (Bearer token, HTTPS)
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        BACKEND (Render / Railway)                    │
│  FastAPI  ──  auth verification  ──  RBAC authorisation              │
│    ├── evidence router    (upload, hash, integrity, chain of custody) │
│    ├── forensics routers  (deeptrace / spytrace / voiceproof /        │
│    │                        cybersleuth) — background job dispatch   │
│    ├── correlation router (entity extraction, timeline, graph)        │
│    ├── reports router     (PDF generation)                           │
│    └── audit router       (immutable event log)                      │
│                                     │                                │
│                    ┌────────────────┴────────────────┐               │
│                    ▼                                 ▼               │
│         ┌────────────────────┐          ┌──────────────────┐        │
│         │  Gemini API        │          │ Forensic Engines │        │
│         │  (explanations     │          │ OpenCV / Andro-  │        │
│         │   ONLY, grounded)  │          │ guard / Librosa  │        │
│         └────────────────────┘          └──────────────────┘        │
└──────────┬──────────────────────────────────────┬──────────────────┘
           │                                      │
           ▼                                      ▼
┌────────────────────────────┐      ┌─────────────────────────────────┐
│  SUPABASE POSTGRESQL       │      │  SUPABASE STORAGE (private)      │
│  profiles, investigations, │      │  evidence originals (immutable) │
│  evidence, analysis_results│      │  processed artefacts, thumbnails│
│  chain_of_custody,         │      └─────────────────────────────────┘
│  correlation_results,      │
│  audit_logs, reports       │◀──── RLS on every table
└────────────────────────────┘
```

Full detail: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)

---

## 🗄 Database Architecture

Eleven tables, all UUID primary keys, all foreign-keyed, all RLS-protected.

| Table | Purpose |
|---|---|
| `profiles` | User profile + role (`investigator` / `supervisor`) |
| `investigations` | Central case container (UUID, case ID, category, priority, status) |
| `investigation_members` | Many-to-many authorised access per investigation |
| `evidence` | File metadata, SHA-256 hash, storage path, uploader, investigation link |
| `analysis_results` | Structured per-module output with status + confidence |
| `evidence_events` | Per-evidence event stream (access, process, export) |
| `forensic_timelines` | Normalised timeline events with source evidence reference |
| `chain_of_custody` | Append-only custody event ledger |
| `generated_reports` | Report metadata and PDF pointer |
| `audit_logs` | Immutable user/system action log |
| `correlation_results` | Evidence-linked correlation with verification status |

---

## 🚀 Installation

### Prerequisites

- **Node.js 18+** and npm
- **Python 3.10+** (Phase 2 backend)
- **Git**
- **VS Code** (recommended)
- A free **Supabase** project (Phase 2)

### Step 1 — Clone and open in VS Code

```bash
cd C:\Users\ABHISHEK\Documents\NewProject
code .
```

### Step 2 — Frontend setup

```bash
cd frontend
npm install
```

### Step 3 — Environment configuration

```bash
cd frontend
copy .env.example .env
```

Open `frontend/.env` and fill in your values:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
VITE_API_BASE_URL=http://localhost:8000/api
```

> **Never commit `.env`.** It is already listed in `.gitignore`.
> The Gemini key and Supabase **service role** key belong in the **backend** `.env` only —
> they must never appear in any `VITE_` variable, because Vite inlines `VITE_*` into
> the JavaScript bundle shipped to the browser.

### Step 4 — Run the development server

```bash
cd frontend
npm run dev
```

Open **http://localhost:3000**.

> If port 3000 is already in use, Vite automatically selects the next free port
> (e.g. `http://localhost:3001`) and prints the URL in the terminal.

### Step 4b — Share the project with someone else

**Instant public link (no account needed)** — from the desktop `Um_Cyber` folder,
double-click `start-share-link.cmd`. It starts the dev server and opens a Cloudflare
quick tunnel, printing a public URL.

```bash
# manual equivalent
cd frontend && npm run dev -- --host
"%USERPROFILE%\Tools\cloudflared.exe" tunnel --url http://localhost:3000 --no-autoupdate
```

Send the `https://<random>.trycloudflare.com` URL to anyone. Quick-tunnel URLs change
on every restart, so for a permanent link deploy the frontend to Netlify (see
[Deployment](#-deployment)).

> Vite's `server.allowedHosts` in `frontend/vite.config.ts` permits `.trycloudflare.com`
> and `.loca.lt` so tunnels are not rejected by the DNS-rebinding guard. Remove those
> entries if you never expose the dev server publicly.

### Step 5 — Demo sign-in

Phase 1 runs in a local demo auth mode so you can explore every screen immediately:

| Role | Email | Password |
|---|---|---|
| Investigator | `investigator@cybersleuth.ai` | `password123` |
| Supervisor | `supervisor@cybersleuth.ai` | `password123` |

Phase 2 replaces this with real Supabase Auth.

### Other frontend commands

```bash
npm run build     # Type-check + production build to dist/
npm run preview   # Serve the production build locally
npm run lint      # ESLint
```

### Step 6 — Backend setup (Phase 2, not yet implemented)

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env          # add SUPABASE_*, GEMINI_API_KEY locally
uvicorn app.main:app --reload   # http://localhost:8000
```

API docs will be at **http://localhost:8000/docs**.

---

## 📡 API Documentation

The full endpoint contract — request schemas, response schemas, status codes, error
format, and background-job polling — is in [`docs/API.md`](./docs/API.md).

Planned surface (Phase 2+):

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service health |
| `GET` | `/api/auth/me` | Current user profile + role |
| `GET` `POST` | `/api/investigations` | List / create investigations |
| `GET` `PUT` | `/api/investigations/{id}` | Read / update investigation |
| `POST` | `/api/evidence/upload` | Secure upload + hash + custody event |
| `GET` | `/api/evidence/{id}` | Evidence metadata |
| `POST` | `/api/evidence/{id}/integrity-check` | Re-verify SHA-256 |
| `POST` | `/api/deeptrace/analyze` | Image / video analysis (background job) |
| `POST` | `/api/spytrace/analyze` | APK static analysis (background job) |
| `POST` | `/api/voiceproof/analyze` | Audio analysis (background job) |
| `POST` | `/api/cybersleuth/analyze` | Artefact extraction + timeline (background job) |
| `POST` `GET` | `/api/correlation/{investigation_id}` | Run / fetch correlation |
| `POST` | `/api/reports/{investigation_id}` | Generate PDF report |
| `GET` | `/api/reports/{id}` | Fetch report metadata / PDF |

---

## 🧪 Testing

**Phase 1 verification (completed):**

| Check | Command | Result |
|---|---|---|
| TypeScript strict type-check | `npx tsc --noEmit` | ✅ 0 errors |
| Production build | `npm run build` | ✅ success (1608 modules, 389.82 kB JS / 117.75 kB gzip) |
| Route render sweep (14 routes) | browser automation | ✅ all render, correct headings |
| Console error sweep | browser automation | ✅ 0 errors |
| Navigation (11 sidebar items) | browser automation | ✅ all present on every route |
| Auth flow (login → dashboard → logout) | browser automation | ✅ works |
| Correlation workflow | browser automation | ✅ timeline + connections + graph render |
| Report generation workflow | browser automation | ✅ generates report ID + download button |

**Phase 2+ test plan** (per the project specification):

- Authentication and session handling
- Role-based access control (Investigator vs Supervisor)
- Investigation creation and validation
- Evidence upload validation (type, size, filename sanitisation)
- SHA-256 calculation and integrity verification
- Metadata extraction per file class
- Each forensic module
- Correlation logic and entity extraction
- Report generation
- API error handling and authorisation failures

---

## 🔐 Security Considerations

Full detail: [`docs/SECURITY.md`](./docs/SECURITY.md).

Implemented in Phase 1:

- **No secrets in the frontend.** Only `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are browser-visible. The Gemini key and Supabase service-role key are backend-only by design.
- **Strict TypeScript** with `noUnusedLocals`, `noImplicitAny`, and `noFallthroughCasesInSwitch`.
- **Client-side SHA-256** pre-computation on upload (informational; the backend remains the authority).
- **Never trust the client.** All authorisation decisions in Phases 2+ are enforced server-side and in the database via RLS — hiding a button is never the access control.

Required in Phases 2+ (deliberately **not** implemented in a frontend-only build):

- Supabase Auth with token verification on every backend request.
- Row Level Security on all eleven tables.
- Private storage buckets with signed, short-lived URLs.
- Service-role usage that explicitly re-checks the caller's authorisation, because the service role bypasses RLS.
- CORS restricted to configured frontend origins.
- Audit logging of every evidence access, process, and export.
- No execution of uploaded files; APK analysis is strictly static.

---

## 🌐 Deployment

### Frontend → Netlify

The repo root contains a ready `netlify.toml`, so **no manual build settings are
needed**.

1. Push the repo to GitHub.
2. Netlify → **Add new site** → **Import an existing project** → connect the repo.
3. Netlify reads `netlify.toml` and auto-configures:

   | Setting | Value |
   |---|---|
   | Base directory | `frontend` |
   | Build command | `npm run build` |
   | Publish directory | `dist` |
   | Node version | `18` |

4. **Site configuration → Environment variables → Add** the public variables:

   ```
   VITE_SUPABASE_URL      = https://<project>.supabase.co
   VITE_SUPABASE_ANON_KEY = <supabase anon key>
   VITE_API_BASE_URL      = https://<your-backend>/api
   ```

5. **Deploy site.** You get a permanent URL: `https://<your-site>.netlify.app`.

> **Only `VITE_` variables are public.** Never put `GEMINI_API_KEY` or
> `SUPABASE_SERVICE_ROLE_KEY` here — they belong in the backend's environment.

**Why SPA routing is configured:** React Router serves routes like `/deeptrace` and
`/investigations/<uuid>` client-side. The `[[redirects]]` block in `netlify.toml` plus
`frontend/public/_redirects` both rewrite unknown paths to `/index.html`, so a direct
link or a page refresh never 404s. Verified locally against the production build.

**Deploy without GitHub (quick preview):**

```bash
npm i -g netlify-cli
cd C:\Users\ABHISHEK\Documents\NewProject
netlify deploy --prod --dir frontend/dist
netlify deploy --prod --dir frontend/dist --alias cybersleuth-ai
```

### Backend → Render / Railway (Phase 2)

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set `SUPABASE_*`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and `FRONTEND_URL` (your Netlify
URL, for CORS) in the platform's environment settings.

### Database, Auth & Storage → Supabase

Apply the migrations from `supabase/migrations/`, enable RLS, and create the private
buckets `evidence-originals`, `evidence-derived`, `reports`.

---

## ⚠️ Known Limitations

These are honest, current constraints — not placeholders for something that "works":

1. **No backend yet.** All analysis actions in Phase 1 return clearly-labelled sample payloads to demonstrate the UI contract. They are **not** real forensic findings.
2. **No real forensic models.** Deepfake detection, synthetic voice detection, and spyware classification are not implemented — no calibrated model is bundled. The UI states this explicitly and distinguishes heuristics from model predictions.
3. **No database.** Investigations and evidence lists are empty until Phase 2. Pages show a "Demo mode" empty state rather than invented data.
4. **No PDF generation.** The report flow is UI-only; the backend renderer arrives in Phase 6.
5. **Demo authentication.** Credentials are validated client-side in Phase 1 and are not a security control.
6. **No deleted-evidence reconstruction.** Deliberately not implemented — reconstruction is only attempted when genuine recoverable source artefacts exist.

---

## 🚀 Future Scope

- **Phase 2–7** as listed in the project status table.
- Additional modules: network traffic analysis, memory forensics, disk image carving, blockchain transaction tracing.
- Collaborative investigation with supervisor annotation and finding approval workflows.
- Cross-case search and a global evidence index with provenance tracking.
- Signed evidence manifests and exportable court bundles.
- On-device model inference for air-gapped deployments.

---

## 📄 License

MIT — see [`LICENSE`](./LICENSE).

---

## 📚 Documentation Index

| Document | Contents |
|---|---|
| [`DEVELOPMENT_STATUS.md`](./DEVELOPMENT_STATUS.md) | Phase-by-phase status and test results |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | System, database, and module design |
| [`docs/API.md`](./docs/API.md) | Endpoint contract and schemas |
| [`docs/SECURITY.md`](./docs/SECURITY.md) | Threat model, controls, and secure development rules |

---

<p align="center">
  <b>CyberSleuth AI</b><br>
  <i>Detect the Threat. Decode the Evidence. Reconstruct the Truth.</i><br><br>
  Built with React · TypeScript · Tailwind CSS · FastAPI · Supabase · Gemini
</p>
