# CyberSleuth AI — Architecture

> Multimodal AI-Powered Digital Forensics & Evidence Reconstruction Platform

This document describes the system design for CyberSleuth AI. It covers the three-layer
architecture, the database model, the four forensic modules, the correlation engine, and
the epistemic model that keeps technical observation separate from AI interpretation.

---

## 1. Design Principles

### 1.1 One investigation, one container
An **investigation** is the single organising unit. Every piece of evidence, every
analysis result, every timeline event, and every report belongs to exactly one
investigation. Modules never own data — they write *findings* into the investigation's
analysis results. This is what makes cross-module correlation possible at all.

### 1.2 Originals are immutable
The uploaded original is **never modified**. Processed artefacts (extracted frames,
thumbnails, waveforms, spectrograms, normalised text) are written to a **separate**
storage path and referenced from `analysis_results`. This preserves evidentiary
integrity and makes hash re-verification meaningful.

### 1.3 Epistemic separation
The platform must never blur these six categories:

| Layer | Meaning | Stored as |
|---|---|---|
| **Observed fact** | Directly extracted from the artefact (byte values, hashes, timestamps) | `analysis_results.findings[].observed` |
| **Extracted artefact** | Derived deterministic output (frames, entities, permissions) | `analysis_results.artifacts[]` |
| **Model prediction** | Output of a calibrated ML model, with a confidence value | `analysis_results.confidence_score` |
| **AI explanation** | Gemini prose grounded in the above | `analysis_results.explanation` |
| **Investigative hypothesis** | Human reasoning connecting findings | `correlation_results` (unverified) |
| **Verified finding** | Hypothesis accepted by an investigator | `correlation_results.verified = true` |

A UI element must never render an AI explanation with the same visual weight as an
observed fact. Gemini may **summarise and explain** structured findings; it may not
**invent** findings, fabricate timestamps, or act as a detection mechanism.

### 1.4 Absence of evidence is stated, not faked
If no calibrated model is configured, the API returns `status: "unavailable"` with a
human-readable reason. The UI shows *"Model not configured"*. It never shows a
plausible-looking confidence number.

---

## 2. System Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PRESENTATION — React 18 + TypeScript + Vite + Tailwind                │
│  ┌───────────┬───────────┬───────────┬───────────┬───────────────┐    │
│  │ Dashboard │Investigat-│  Evidence │ Correlation│    Reports    │    │
│  │           │  ions     │   Vault   │   Engine   │               │    │
│  └───────────┴─────┬─────┴─────┬─────┴─────┬─────┴───────────────┘    │
│                    │           │           │                          │
│           ┌────────┴───────────┴───────────┴────────┐                 │
│           │   DeepTrace │ SpyTrace │ VoiceProof │    │ CyberSleuth    │
│           │     AI        │   AI      │   AI      │     │     AI        │
│           └────────────────┴──────────┴───────────┘     └──────────────┘  │
│                                                                         │
│  Cross-cutting: AuthContext · Axios apiClient · RouteGuard              │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │  HTTPS + Authorization: Bearer <supabase_jwt>
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  APPLICATION — FastAPI (Python)                                        │
│                                                                         │
│  Middleware      CORS allowlist · request ID · structured logging       │
│  Auth            Supabase JWT verification → AuthContext (user, role)   │
│  Authorisation   require_role() · require_case_access()  ← not UI hiding │
│  Routers         evidence · deeptrace · spytrace · voiceproof ·         │
│                  cybersleuth · correlation · reports · audit · health   │
│  Services        storage · hashing · gemini · jobs · audit              │
│  Forensic engines deeptrace/ spytrace/ voiceproof/ cybersleuth/          │
└──────┬─────────────────────────────────────────────┬───────────────────┘
       │                                             │
       │ Supabase client (service role, with explicit │
       │ per-resource authorisation re-check)         │  Gemini API
       ▼                                             ▼
┌──────────────────────────────┐        ┌───────────────────────────────┐
│  DATA — Supabase PostgreSQL  │        │  AI — Google Gemini           │
│  11 tables · RLS on every    │        │  Explanations, summaries,     │
│  table · UUID PKs · FKs      │        │  correlation narratives,      │
│  Storage: private buckets    │        │  report drafts.               │
└──────────────────────────────┘        │  NEVER a detection engine.    │
                                        └───────────────────────────────┘
```

### 2.1 Backend layer responsibilities

| Layer | Path | Responsibility |
|---|---|---|
| Routers | `app/api/` | HTTP contract, validation, status codes |
| Schemas | `app/schemas/` | Pydantic request/response models |
| Core | `app/core/` | Config, security, logging, exceptions |
| Security | `app/security/` | Supabase token verification, RBAC, case access |
| Services | `app/services/` | Storage, hashing, Gemini client, job dispatcher, audit writer |
| Forensic | `app/forensic/` | The four module engines (pure analysis, no I/O) |
| Correlation | `app/correlation/` | Entity normalisation, timeline builder, graph builder |
| Reports | `app/reports/` | PDF renderer |
| Database | `app/database/` | Supabase client factory, repositories |

The forensic engines are deliberately **pure functions over bytes → structured findings**.
They receive a file path and configuration, and return a serialisable dict. They never
touch the database, never call the network, and never modify the original.

---

## 3. Database Model

All tables use UUID primary keys (`gen_random_uuid()`), `created_at`/`updated_at`
timestamps, and foreign keys with explicit `ON DELETE` behaviour.

```
profiles ──────────────┐
  id (uuid, = auth.uid)│
  full_name            │
  role (enum)          │
  institution          │
                       │
investigation_members ─┴──────────┐
  investigation_id  ─────────────┤
  user_id                          │
  role (enum)                      │
  UNIQUE(investigation_id,user_id) │
                                  ▼
investigations ──────────────── evidence ──────────── analysis_results
  id (uuid)                      id (uuid)             id (uuid)
  case_id (unique, human)        investigation_id       evidence_id
  title                          original_filename      module (enum)
  description                    file_size              status (enum)
  category                       mime_type              result_data (jsonb)
  priority (enum)                sha256_hash            confidence_score
  status (enum)                  storage_path           error_message
  owner_id ─────────────────────> uploaded_by
  notes                          uploaded_at            forensic_timelines
  created_at/updated_at          processed_at              id (uuid)
                                                ▲         evidence_id
                                                │         event_timestamp
  evidence_events ───────────────┘         investigation_id
    id (uuid)                               event_type
    evidence_id                             source_file
    event_type (enum)                       extracted_content
    actor_id                                entities (jsonb)
    details                                 evidence_id (ref)
    created_at
                                                correlation_results
  chain_of_custody                            id (uuid)
    id (uuid)                                 investigation_id
    evidence_id                               source_evidence_id
    event_type (enum)                         finding_id
    actor_id                                  correlation_type
    details                                   description
    created_at                                confidence
                                               verified (bool)
  audit_logs                                   created_at
    id (uuid)
    user_id / user_name                      generated_reports
    action                                      id (uuid)
    resource                                   investigation_id
    resource_id                                title
    ip_address                                 status (enum)
    created_at                                 pdf_path
                                               generated_by
                                               created_at
```

### 3.1 Table responsibilities

| Table | Responsibility |
|---|---|
| `profiles` | One row per Supabase Auth user; carries the `role` used by RBAC. Created by trigger on `auth.users` insert. |
| `investigations` | The case container. `case_id` is the human-readable reference; `id` is the UUID used everywhere internally. |
| `investigation_members` | Explicit many-to-many authorisation. A user may read an investigation only if they are the owner **or** a member. |
| `evidence` | File metadata only — never file bytes. `sha256_hash` is the integrity anchor. `storage_path` points into a private bucket. |
| `analysis_results` | One row per (evidence, module) analysis. `result_data` is `jsonb` holding the module's structured findings. |
| `evidence_events` | Per-evidence event stream used by the evidence detail timeline. |
| `forensic_timelines` | Normalised, cross-source timeline events. `source_file` preserves the originating artefact name. |
| `chain_of_custody` | Append-only custody ledger. Rows are never updated or deleted. |
| `audit_logs` | Immutable user/system action log across the whole platform. |
| `correlation_results` | A proposed relationship between evidence records, with reason, confidence, and human verification state. |
| `generated_reports` | Report metadata and the pointer to the rendered PDF artefact. |

### 3.2 Storage layout

Private Supabase buckets:

| Bucket | Contents | Mutability |
|---|---|---|
| `evidence-originals` | Uploaded originals, byte-identical | **Immutable** — no update policy |
| `evidence-derived` | Frames, thumbnails, waveforms, spectrograms, normalised text | Writable by the processing pipeline only |
| `reports` | Rendered PDF reports | Writable by the report service only |

Object path convention:

```
evidence-originals/{investigation_id}/{evidence_id}/{original_filename}
evidence-derived/{evidence_id}/frames/frame_000123.jpg
evidence-derived/{evidence_id}/audio/spectrogram.png
reports/{investigation_id}/{report_id}.pdf
```

The original filename is preserved verbatim for forensic fidelity, but is **never** used
to construct a filesystem path — it is sanitised for display and the storage path is
generated from UUIDs only, preventing path traversal.

### 3.3 Row Level Security

Every table has RLS enabled. The general pattern:

```sql
-- helper: can the current user read this investigation?
create or replace function public.can_access_investigation(p_investigation uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.investigation_members m
    where m.investigation_id = p_investigation
      and m.user_id = auth.uid()
  );
$$;

create policy evidence_select on public.evidence
  for select using (public.can_access_investigation(investigation_id));
```

The API exposes the authenticated user's JWT to Postgres via `request.jwt.claims`
(Supabase client) or an `app.current_user_id` session variable (direct connection),
so RLS evaluates against the real caller — not the service role.

> **Service-role caveat.** The backend uses the service-role key for privileged writes.
> The service role **bypasses RLS**. Therefore the backend **must** re-verify the
> authenticated user's authorisation for every single resource it touches. This is
> enforced in `app/security/authorisation.py` and is not optional.

---

## 4. Forensic Module Design

All four modules follow the same contract.

### 4.1 Common pipeline

```
  upload ──► validate ──► hash (SHA-256) ──► store original (immutable)
                                                    │
                                    ┌───────────────┴───────────────┐
                                    ▼                               ▼
                            metadata extraction            module engine
                            (type, size, mime,          (pure fn: bytes → findings)
                             dimensions, duration)              │
                                    │                            ▼
                                    │                   analysis_results row
                                    │                   (status, result_data,
                                    │                    confidence, error)
                                    ▼
                            chain_of_custody event
```

### 4.2 Module contracts

#### DeepTrace AI — image & video forensics

```python
class DeepTraceRequest(BaseModel):
    evidence_id: uuid.UUID

class DeepTraceFinding(BaseModel):
    label: str                    # "Metadata", "ELA compression", "Frame timestamps"
    value: str
    status: Literal["info", "success", "warning", "error"]
    method: Literal["heuristic", "model"]   # ← never conflate the two
    confidence: float | None = None          # only when a calibrated model produced it
    frames: list[FrameReference] = []
```

**Capabilities:** EXIF/metadata extraction · dimension & colour-space analysis · OpenCV
frame extraction at configurable intervals · frame thumbnails · Error Level Analysis
(ELA) for re-compression detection · noise-variance heuristic · optional pluggable
deepfake model.

**Constraint:** unusual metadata is reported as a *heuristic observation*, never as
"deepfake". The `method` field is what the UI keys off to label a row as
`Heuristic check` versus `Model prediction`.

#### SpyTrace AI — Android analysis

```python
class SpyTraceRequest(BaseModel):
    evidence_id: uuid.UUID

class SpyTraceFinding(BaseModel):
    package_name: str
    version_name: str | None
    sdk_min: int | None
    sdk_target: int | None
    permissions: list[str]
    services: list[str]
    receivers: list[str]
    activities: list[str]
    domains: list[str]
    suspicious_combinations: list[PermissionCombination]
    risk_indicators: list[RiskIndicator]
```

**Capabilities:** Androguard APK parsing · `AndroidManifest.xml` decoding · permission
extraction with sensitivity classification · dangerous-permission combination rules ·
background service and broadcast receiver identification · domain/URL string extraction ·
risk scoring.

**Constraint:** **static analysis only.** The APK is never installed, never executed,
and never passed to a sandbox on the API host. A permission combination raises a
*risk indicator*, not a "this is spyware" verdict — legitimate apps request the same
permissions.

#### VoiceProof AI — audio forensics

```python
class VoiceProofRequest(BaseModel):
    evidence_id: uuid.UUID

class VoiceProofFinding(BaseModel):
    duration_seconds: float
    sample_rate: int
    channels: int
    codec: str | None
    peak_dbfs: float
    clipping_ratio: float
    silence_ratio: float
    anomalies: list[AudioAnomaly]      # with timestamp ranges
    synthetic_voice: ModelPrediction | None   # null when no model is configured
```

**Capabilities:** Librosa waveform + spectrogram generation · loudness/clipping/silence
analysis · spectral centroid & zero-crossing rate features · segment-level anomaly
detection · optional synthetic-voice model.

**Constraint:** the module does **not** identify a speaker's real-world identity.
Synthetic-voice output is a model prediction with stated limitations, never proof.

#### CyberSleuth AI — artefact extraction

```python
class CybersleuthRequest(BaseModel):
    evidence_id: uuid.UUID

class CybersleuthFinding(BaseModel):
    record_count: int
    timestamps: list[ExtractedTimestamp]
    entities: list[ExtractedEntity]
    urls: list[str]
    domains: list[str]
    emails: list[str]
    phones: list[str]
    duplicates: list[DuplicateRecord]
    messages: list[MessageGroup]
    classified_events: list[ClassifiedEvent]
    timeline: list[TimelineEvent]
    graph: RelationshipGraph
```

**Capabilities:** TXT/CSV/JSON/XML/EML/PDF/log parsing · timestamp extraction and
normalisation (multiple formats, timezone-aware) · spaCy entity extraction · URL and
domain extraction · email and phone pattern extraction · duplicate record detection ·
message grouping · event classification · chronological timeline · NetworkX relationship
graph.

**Constraint:** **deleted evidence is never fabricated.** Reconstruction is attempted
only when genuinely recoverable source artefacts are present, and the output states
which artefact the recovered content came from.

---

## 5. Correlation Engine

The engine is the platform's central differentiator. It never analyses files itself —
it reads structured `analysis_results` and relates them.

### 5.1 Pipeline

```
  analysis_results (all modules, one investigation)
        │
        ▼
  ① Retrieve ────────────► structured findings per evidence
        │
        ▼
  ② Normalise ───────────► timestamps → UTC ISO-8601; entities → canonical form
        │
        ▼
  ③ Extract ─────────────► shared indicators: domains, emails, IPs, device IDs,
        │                     accounts, file names, coordinates
        ▼
  ④ Match ───────────────► pairwise comparison → candidate relationships
        │                     (timestamp proximity, shared indicator,
        │                      same-entity co-occurrence)
        ▼
  ⑤ Rank ────────────────► score each relationship by rule confidence
        │
        ▼
  ⑥ Timeline ────────────► merge all events into one chronology
        │
        ▼
  ⑦ Graph ───────────────► NetworkX DiGraph: evidence + entities as nodes,
        │                     relationships as edges
        ▼
  ⑧ Explain ─────────────► Gemini generates prose grounded in the structured
                            relationship set — no new facts
        │
        ▼
  ⑨ Persist ─────────────► correlation_results rows (verified = false)
                            + investigator verification workflow
```

### 5.2 Relationship record

Every correlation is stored with full provenance:

```python
class CorrelationResult(BaseModel):
    investigation_id: uuid.UUID
    source_evidence_id: uuid.UUID      # ← required
    target_evidence_id: uuid.UUID      # ← required
    finding_id: uuid.UUID | None       # ← the analysis_result that supports it
    correlation_type: str              # "temporal" | "shared_indicator" | "entity_overlap"
    reason: str                        # human-readable justification
    supporting_data: dict              # the actual extracted values
    timestamp: datetime | None
    confidence: float | None           # rule-derived; None if unsupported
    verified: bool = False             # investigator must confirm
    is_hypothesis: bool = True         # correlation is a hypothesis, not a fact
```

Nothing is auto-promoted to a verified finding. The investigator verifies.

### 5.3 Gemini grounding rules

The Gemini prompt receives **only** the serialised structured findings and
correlation records — never raw file bytes. The response is required to:

1. Reference only evidence IDs present in the input.
2. Never introduce a timestamp, entity, or indicator that is absent from the input.
3. Mark uncertainty explicitly.
4. Avoid language implying guilt or identity inference.

If the input set is empty, the API returns a "no findings to explain" response rather
than invoking the model at all.

---

## 6. Background Job Processing

Long-running analysis (frame extraction, APK parsing, spectrogram rendering, correlation
across many evidence items) must not block the HTTP request.

```
  POST /api/deeptrace/analyze
        │
        ├─► validate request, authorise evidence access
        ├─► create analysis_results row  (status = "pending")
        ├─► dispatch background job       → returns 202 + analysis_id
        │
        └─► worker picks up job
              ├─► status = "running"
              ├─► run engine (bytes → findings)
              ├─► status = "completed" | "failed" (+ error_message)
              └─► write derived artefacts to storage
```

The client polls `GET /api/analysis/{id}/status`. The worker implementation is
swappable — in-process `BackgroundTasks` for local development, and a Celery/RQ worker
with Redis for production, behind the same `JobDispatcher` interface.

---

## 7. Frontend Structure

```
frontend/src/
├── components/
│   ├── layout/          Sidebar · TopNav · Layout
│   ├── ui/              Button · Card · StatCard · Badge · Input · EmptyState · LoadingSpinner
│   └── RouteGuard.tsx   ProtectedRoute · GuestRoute
├── pages/               16 route components (one per screen)
├── context/AuthContext  Supabase-ready session state
├── services/api.ts      Axios client + typed endpoint wrappers
├── hooks/               (Phase 2: TanStack Query hooks)
├── types/               Shared TypeScript domain types
├── utils/               cn() · formatting helpers
└── App.tsx              Route table
```

**Path aliases:** `@/*` → `src/*`, `@/ui/*` → `src/components/ui/*`. Both `tsconfig.json`
and `vite.config.ts` must declare them, using **regex** aliases in Vite so that
`@/ui/...` is not captured by the broader `@/...` prefix.

**State strategy (Phase 2):** TanStack Query for all server state; local `useState` only
for form drafts and ephemeral UI state. Never mirror server data into local state.

---

## 8. Deployment Topology

| Component | Platform | Configuration |
|---|---|---|
| Frontend | Vercel | Build `npm run build`, output `dist`; env vars from Vercel project settings |
| Backend | Render / Railway | `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; env vars from platform dashboard |
| Database + Auth + Storage | Supabase | Migrations applied via Supabase CLI or SQL editor; RLS enabled before first write |
| CI | GitHub Actions | `npm run build` + `pytest` on every push to `main` |

CORS is restricted to the configured frontend origins via `FRONTEND_URL` /
`CORS_ORIGINS`. Credentials are not shared across origins.

---

## 9. Extending the Platform

To add a fifth forensic module:

1. Implement `app/forensic/<module>/engine.py` exposing
   `analyse(file_path: Path, config: ModuleConfig) -> dict` — pure, no I/O.
2. Add `app/forensic/<module>/schemas.py` with the request/response models.
3. Add `app/api/<module>.py` with the `analyze` endpoint and job dispatch.
4. Add the module to the `module` enum on `analysis_results`.
5. Add a frontend page under `src/pages/` and a sidebar entry in `Sidebar.tsx`.
6. Add the module to the correlation engine's extraction switch so its indicators
   participate in cross-evidence matching.

No changes to the core schema, storage layer, or correlation engine are required.
