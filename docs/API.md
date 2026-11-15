# CyberSleuth AI - API Reference (as implemented)

> Base URL (local dev): `http://127.0.0.1:8000/api`
> Base URL (production): `https://<your-api-host>/api`
> Interactive docs: `/docs` (Swagger UI) · `/redoc` · `/openapi.json`

This reference describes the API as it is actually implemented in this repository, verified by the 41-test suite in `backend/tests/`. Where this document and the code disagree, the code and the OpenAPI schema (`/openapi.json`) win.

---

## 1. Conventions

### 1.1 Authentication

The backend issues its **own** short-lived HS256 JWT pair at login/register. Send the access token on every protected request:

```http
Authorization: Bearer <access_token>
```

- Access tokens expire after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default **30**).
- Refresh tokens expire after `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (default **7**) and are exchanged via `POST /api/auth/refresh`.
- **Authorisation is always enforced server-side and in the database (RLS).** A hidden button is never a control.
- All local development uses the same HS256 scheme; when `SUPABASE_URL` is configured, identities are Supabase-managed, but the pipeline is identical.

### 1.2 Roles

| Role | Capabilities |
|---|---|
| `investigator` | Create investigations, upload and manage evidence, run analysis, view findings, generate reports |
| `supervisor` | Everything an investigator can do **for cases they are a member of**, plus read access to every audit log entry |

### 1.3 Content types

`application/json` for everything except evidence upload, which is `multipart/form-data`.

### 1.4 Error format

Errors use FastAPI's default shape:

```json
{ "detail": "Evidence not found" }
```

Validation failures return `422` with an `errors` array:

```json
{
  "detail": "The request body is not valid.",
  "errors": [{ "loc": ["body", "email"], "msg": "value is not a valid email address" }]
}
```

| Status | Meaning |
|---|---|
| `400` | Malformed request / rejected by upload validation |
| `401` | Missing, expired or invalid token |
| `403` | Authenticated but role insufficient |
| `404` | Not found (or not visible to you — see below) |
| `409` | Conflict (e.g. duplicate `case_id`, module already provided) |
| `413` | Upload exceeds `MAX_UPLOAD_SIZE_MB` (default 100 MB) |
| `422` | Schema validation failed |
| `429` | Rate limit exceeded; `Retry-After` header set (auth endpoints) |
| `500` | Unexpected server error |

> `404` is deliberately returned for resources the caller may not see, so existence is never leaked.

### 1.5 Error-free quick checks

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/health` | Liveness/dependency status, no auth. Also mounted at `GET /health`. |

```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "ok",
  "storage": "ok",
  "forensic_modules": true,
  "ai_explanation": true,
  "time": "2026-11-14T17:31:23.811682Z"
}
```

---

## 2. Authentication

### `POST /api/auth/register` — 201

```json
{ "full_name": "Lead Investigator", "email": "lead@agency.gov",
  "password": "Strong!2026", "confirm_password": "Strong!2026", "role": "investigator" }
```

Returns `{ user, access_token, refresh_token, expires_in }`. Rate limited to **5/min per IP**. Duplicate email → `409`. `role` is one of `investigator` (default) / `supervisor`.

### `POST /api/auth/login` — 200

```json
{ "email": "lead@agency.gov", "password": "Strong!2026" }
```

Returns the same envelope as register. Rate limited to **10/min per IP**; excess → `429` with `Retry-After`. Wrong credentials → `401` (audited as `login_failed`).

### `POST /api/auth/refresh` — 200

```json
{ "refresh_token": "..." }
```

Exchanges a refresh token for a fresh pair. The profile is re-read **under RLS**, so a deleted/disabled account can never refresh.

### `GET /api/auth/me` — 200 · `POST /api/auth/logout` — 200

`/me` returns the caller's profile; `/logout` writes an audit event and the client discards its tokens (stateless access tokens).

---

## 3. Investigations

### `GET /api/investigations` — 200 · `POST /api/investigations` — 201

Create body:

```json
{ "case_id": "CASE-2026-0147", "title": "Operation Silent Whisper",
  "description": "…", "category": "spyware", "priority": "high",
  "status": "active", "notes": "…", "member_ids": [] }
```

`priority` ∈ `low|medium|high|critical`; `status` ∈ `draft|active|review|closed|archived`. Duplicate `case_id` → **`409`**.

Response includes `evidence_count`, `analysis_count`, `owner_name`, `assigned_users`.

### `GET /api/investigations/{id}` — 200

Returns the investigation plus members, evidence list and analysis runs.

### `PATCH /api/investigations/{id}` — 200

Partial update (`title`, `description`, `category`, `priority`, `status`, `notes`).

### `DELETE /api/investigations/{id}` — 204

Owner or supervisor. Cascades to evidence and results.

### `GET/POST /api/investigations/{id}/members` · `DELETE /api/investigations/{id}/members/{user_id}`

Member management; supervisors and the owner may manage membership.

---

## 4. Evidence

### `GET /api/evidence?investigation_id=&search=&evidence_type=` — 200

### `POST /api/evidence/upload` — 201 (`multipart/form-data`)

Fields: `investigation_id` (string UUID), `file`.

Server-side pipeline: stream → size cap (`MAX_UPLOAD_SIZE_MB`) → allow-list validation (extension + sniffed MIME) → SHA-256 → store under immutable originals bucket → **re-hash stored object and compare** → row → custody `upload` event → audit event.

```json
{
  "id": "9b8a…", "original_filename": "field-screen-photo.jpg",
  "file_size": 38715, "mime_type": "image/jpeg",
  "sha256_hash": "62cfe89f…", "status": "uploaded",
  "uploaded_at": "2026-11-14T22:00:00Z", "metadata": { "detected_mime": "image/jpeg", "type": "image", "exif": { "Make": "Google" } }
}
```

### `GET /api/evidence/{id}` — 200 · `GET /api/evidence/{id}/download` — 200

Download streams the stored bytes with `X-Evidence-SHA256`; integrity can be checked locally.

### `POST /api/evidence/{id}/integrity-check` — 200

Recomputes the stored object's SHA-256:

```json
{ "evidence_id": "…", "expected_sha256": "62cf…", "actual_sha256": "62cf…", "intact": true, "checked_at": "…" }
```

### `GET /api/evidence/{id}/custody` — 200 · `GET /api/evidence/{id}/custody/verify` — 200 · `GET /api/evidence/{id}/events` — 200

Custody returns the hash-chained ledger; `verify` replays it:

```json
{ "evidence_id": "…", "event_count": 4, "valid": true, "broken_at": null, "head_hash": "ab12…" }
```

---

## 5. Analysis modules (synchronous)

Each module endpoint has the **same contract** and runs synchronously on the backend (`asyncio.to_thread` for CPU-bound work):

```
POST /api/deeptrace/analyze
POST /api/spytrace/analyze
POST /api/voiceproof/analyze
POST /api/cybersleuth/analyze
```

Request:

```json
{ "evidence_id": "9b8a…", "options": {} }
```

Response (200) — stored analysis row:

```json
{
  "id": "…", "evidence_id": "…", "module": "deeptrace", "status": "completed",
  "confidence_score": null,
  "created_at": "…", "completed_at": "…",
  "result_data": {
    "module": "deeptrace", "status": "completed", "summary": "…",
    "sha256": "62cf…", "mime": "image/jpeg", "dimensions": "1280 × 720",
    "findings": [
      { "label": "EXIF capture time", "detail": "…", "method": "measured", "severity": "info", "value": { "…": "…" } }
    ],
    "timeline": [ { "timestamp": "2026-11-09T21:14:22+00:00", "label": "EXIF capture", "source": "sample.jpg", "details": "…", "confidence": null } ],
    "metadata": { "exif": { "…": "…" } },
    "derived_files": []
  }
}
```

`method` ∈ `measured | heuristic | model` — `confidence_score` stays `null` for heuristic-only modules, exactly as the UI labels them.

### `GET /api/analysis/results?investigation_id=&evidence_id=&module=&limit=` — 200
### `GET /api/analysis/results/{result_id}` — 200

---

## 6. Correlation

### `POST /api/correlation/{investigation_id}` — 200

Runs the deterministic correlation engine over every analysis result in the case:

1. Collects events from timelines and findings (findings are included as undated entity carriers).
2. Normalises entities and **attaches each artefact's own SHA-256** to its events (so a hash pasted into a chat links to the APK whose hash it is).
3. Detects shared entities, identical timestamps (`timestamp_match`), and sub-120s cross-module proximity (`temporal_proximity`).
4. Replaces any previous `correlation_results` rows and (if `GEMINI_API_KEY` is set and connections exist) asks Gemini — grounded strictly in the findings — for an explanation.
5. Returns the persisted findings, timeline, connections, graph and explanation.

```json
{
  "investigation_id": "9045…",
  "timeline": [ { "timestamp": "…", "label": "…", "source": "…", "module": "cybersleuth", "details": "…", "evidence_id": "…", "entities": ["url:https://…"] } ],
  "connections": [ { "source": "spytrace:Embedded network endpoints", "target": "cybersleuth:Message from R", "connection_type": "shared_entity", "description": "Both observations reference the same url 'https://archive.newpipe.net/fdroid/repo'.", "confidence": 0.9, "evidence_ids": ["…", "…"], "timestamp": null } ],
  "graph": { "nodes": […], "edges": […] },
  "findings": […],
  "explanation": { "available": true, "text": "{…}", "model": "gemini-3.5-flash" },
  "generated_at": "…"
}
```

### `GET /api/correlation/{investigation_id}` — 200

Same shape, computed without calling Gemini (`explain=False`), plus persisted finding rows.

---

## 7. Reports

### `GET /api/reports?investigation_id=` — 200 · `POST /api/reports/{investigation_id}` — 201

```json
{ "title": "CASE-2026-0147 — Operation Silent Whisper — Forensic Report",
  "include_evidence": true, "include_custody": true,
  "include_analysis": true, "include_correlation": true }
```

Renders a professional PDF server-side (investigation summary, evidence inventory with SHA-256, metadata appendix, custody ledger, module findings, correlation connections, limitations/review section), stores it in the reports bucket, and returns the row with `status: "ready"` and a `download_url`.

### `GET /api/reports/{id}` — 200 · `GET /api/reports/{id}/download` — 200

Download returns `Content-Type: application/pdf`, `Content-Disposition`, and `X-Report-SHA256` for local verification.

---

## 8. Audit logs

### `GET /api/audit-logs?action=&resource=&resource_id=&limit=100&offset=0` — 200

Append-only log: `login`, `login_failed`, `logout`, `register`, `upload`, `upload_rejected`, `analyze`, `correlate`, `generate_report`, `download_report`, `update`, `delete`.

Reading is restricted by RLS: users see their own entries, supervisors see all.

### `GET /api/audit-logs/count` — 200

---

## 9. Dashboard

### `GET /api/dashboard/stats` — 200

```json
{ "total_investigations": 2, "active_investigations": 2,
  "evidence_files": 6, "analysis_runs": 7,
  "pending_reviews": 1, "total_evidence_bytes": 9247605,
  "module_runs": { "deeptrace": 2, "spytrace": 1, "voiceproof": 1, "cybersleuth": 3 },
  "recent_investigations": [ { "id": "…", "case_id": "CASE-2026-0147", "…": "…" } ],
  "generated_at": "…" }
```
