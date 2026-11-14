# CyberSleuth AI — API Reference

> Base URL (local): `http://localhost:8000/api`
> Base URL (production): `https://<your-api-host>/api`
> Interactive docs: `/docs` (Swagger UI) · `/redoc` · `/openapi.json`

**Status:** This is the Phase 2+ API contract. The Phase 1 frontend already ships a
typed Axios client (`frontend/src/services/api.ts`) matching these paths, so the
frontend switches from demo mode to live data as soon as the backend is running.

---

## 1. Conventions

### 1.1 Authentication

Supabase Auth issues a JWT. Send it on every protected request:

```http
Authorization: Bearer <supabase_access_token>
```

The backend verifies the token signature with Supabase, then extracts the user id and
role. **Authorisation is always enforced server-side.** A hidden or disabled button is
never a security control.

### 1.2 Roles

| Role | Capabilities |
|---|---|
| `investigator` | Create investigations, upload and manage evidence, run analysis, view findings, generate reports |
| `supervisor` | View authorised investigations, review findings, review reports, access audit information, approve/reject findings |

A supervisor may only see investigations where they appear in `investigation_members`
or where they are the owner.

### 1.3 Content types

- JSON for everything except evidence upload.
- `multipart/form-data` for evidence upload.

### 1.4 Error format

All errors use a consistent envelope:

```json
{
  "error": {
    "code": "EVIDENCE_NOT_FOUND",
    "message": "Evidence '8f2c...' does not exist or is not accessible to you.",
    "detail": null,
    "request_id": "req_01HZX9K2M7"
  }
}
```

| Status | Meaning |
|---|---|
| `400` | Malformed request / validation failure |
| `401` | Missing or invalid token |
| `403` | Authenticated but not authorised for this resource |
| `404` | Resource does not exist **or** is not visible to the caller |
| `409` | Conflict (duplicate case ID, analysis already running) |
| `413` | Upload exceeds the size limit |
| `415` | Unsupported file type |
| `422` | Pydantic schema validation failed |
| `429` | Rate limit exceeded (`Retry-After` header set) |
| `500` | Unexpected server error |
| `503` | A required dependency is unavailable (e.g. AI model not configured) |

> `404` is deliberately used instead of `403` for resources the caller may not see,
> so that resource existence is not leaked.

### 1.5 Long-running operations

Analysis endpoints return **`202 Accepted`** with an `analysis_id`. Poll
`GET /api/analysis/{analysis_id}/status` until `status` is `completed` or `failed`.

---

## 2. Health

### `GET /api/health`

Service liveness and dependency status. No authentication required.

**Response `200`**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2026-11-13T09:42:11.204Z",
  "services": {
    "database": "ok",
    "storage": "ok",
    "ai": "not_configured"
  }
}
```

`ai: "not_configured"` means `GEMINI_API_KEY` is absent. Analysis modules that do not
require Gemini still function; explanation features return `503` with
`AI_SERVICE_UNAVAILABLE`.

---

## 3. Authentication

### `GET /api/auth/me`

Returns the authenticated user's profile and role.

**Response `200`**

```json
{
  "id": "3f8a1c2e-5b7d-4a91-8e3f-9c2d1b6a4f70",
  "email": "investigator@cybersleuth.ai",
  "full_name": "Jane Investigator",
  "role": "investigator",
  "institution": "Digital Forensics Unit",
  "created_at": "2026-01-08T11:04:22.000Z"
}
```

### `PATCH /api/auth/me`

Update the caller's own profile.

```json
{ "full_name": "Jane Investigator", "institution": "Cybercrime Unit" }
```

Only `full_name` and `institution` are updatable. `role` cannot be changed via this
endpoint — roles are assigned by a supervisor or directly in the database.

---

## 4. Investigations

### `GET /api/investigations`

List investigations the caller is authorised to view.

**Query parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `status` | `draft\|active\|review\|closed\|archived` | — | Filter |
| `priority` | `low\|medium\|high\|critical` | — | Filter |
| `category` | string | — | Filter |
| `search` | string | — | Matches `title` or `case_id` |
| `limit` | int | 50 | 1–200 |
| `offset` | int | 0 | Pagination offset |

**Response `200`**

```json
{
  "items": [
    {
      "id": "9b2d4e6a-1c3f-4a5b-8d7e-6f5a4b3c2d1e",
      "case_id": "CASE-2026-001",
      "title": "Coordinated Intrusion via Compromised Mobile App",
      "description": "Suspected spyware deployment...",
      "category": "Cyber Intrusion",
      "priority": "high",
      "status": "active",
      "owner_id": "3f8a1c2e-5b7d-4a91-8e3f-9c2d1b6a4f70",
      "assigned_users": ["3f8a1c2e-..."],
      "notes": "Awaiting carrier records.",
      "evidence_count": 7,
      "analysis_count": 11,
      "created_at": "2026-11-01T08:12:00.000Z",
      "updated_at": "2026-11-12T16:40:00.000Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### `POST /api/investigations`

Create an investigation. The `id` UUID is generated server-side. `case_id` must be
unique across the platform.

```json
{
  "case_id": "CASE-2026-002",
  "title": "Suspected Deepfake Voice Call — Extortion Case",
  "description": "Victim reports a synthetic voice used to request funds.",
  "category": "Fraud Investigation",
  "priority": "critical",
  "assigned_users": ["3f8a1c2e-5b7d-4a91-8e3f-9c2d1b6a4f70"],
  "notes": "Initial intake."
}
```

**Response `201`** — the created investigation object.

**Errors:** `409` duplicate `case_id` · `422` validation failure.

### `GET /api/investigations/{investigation_id}`

Full investigation record including nested `evidence`, `analysis_results`, and
`timeline`.

**Response `200`**

```json
{
  "id": "9b2d4e6a-1c3f-4a5b-8d7e-6f5a4b3c2d1e",
  "case_id": "CASE-2026-001",
  "title": "Coordinated Intrusion via Compromised Mobile App",
  "category": "Cyber Intrusion",
  "priority": "high",
  "status": "active",
  "description": "Suspected spyware deployment...",
  "notes": "Awaiting carrier records.",
  "owner_id": "3f8a1c2e-...",
  "created_at": "2026-11-01T08:12:00.000Z",
  "updated_at": "2026-11-12T16:40:00.000Z",
  "evidence": [ /* evidence objects */ ],
  "analysis_results": [ /* analysis objects */ ],
  "timeline": [
    {
      "event_timestamp": "2026-11-02T08:14:22.000Z",
      "event_type": "message",
      "source_file": "chat_export.json",
      "extracted_content": "User A logged in",
      "entities": ["user_a"],
      "evidence_id": "7c1e2a3b-..."
    }
  ]
}
```

### `PUT /api/investigations/{investigation_id}`

Update mutable fields. `id`, `created_at`, and `owner_id` are immutable.

```json
{
  "title": "Updated title",
  "status": "review",
  "priority": "critical",
  "assigned_users": ["..."],
  "notes": "Escalated for supervisor review."
}
```

**Response `200`** — the updated investigation.

### `DELETE /api/investigations/{investigation_id}`

Soft-archives an investigation (`status = "archived"`). Evidence and analysis results
are retained for evidentiary integrity — nothing is hard-deleted.

---

## 5. Evidence Vault

### `POST /api/evidence/upload`

Upload a file into the private evidence store.

**Content type:** `multipart/form-data`

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | binary | yes | The original file |
| `investigation_id` | uuid | no | Associate with an investigation |

**Behaviour, in order**

1. Authenticate; verify the caller may write to the target investigation.
2. Validate extension against `ALLOWED_EXTENSIONS` → `415` on mismatch.
3. Validate size against `MAX_UPLOAD_SIZE_MB` → `413` on exceed.
4. Sanitise the filename for display (the stored object path uses UUIDs only).
5. Compute SHA-256 **before** storing.
6. Store the original in `evidence-originals` (immutable bucket).
7. Recompute SHA-256 from the stored bytes and compare → `500` `EVIDENCE_CORRUPTED` on mismatch.
8. Extract metadata (dimensions, duration, codec, page count, record count).
9. Insert the `evidence` row and a `chain_of_custody` row (`event_type = "upload"`).
10. Write an `audit_logs` row.

**Response `201`**

```json
{
  "id": "7c1e2a3b-4d5e-6f70-8192-a3b4c5d6e7f8",
  "investigation_id": "9b2d4e6a-1c3f-4a5b-8d7e-6f5a4b3c2d1e",
  "original_filename": "surveillance_footage.mp4",
  "file_size": 2516582400,
  "mime_type": "video/mp4",
  "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "storage_path": "evidence-originals/9b2d4e6a-.../7c1e2a3b-.../surveillance_footage.mp4",
  "status": "uploaded",
  "metadata": {
    "width": 1920,
    "height": 1080,
    "duration_seconds": 94.3,
    "codec": "h264",
    "frame_rate": 30.0
  },
  "uploaded_by": "3f8a1c2e-...",
  "uploaded_at": "2026-11-13T09:42:11.204Z",
  "processed_at": null
}
```

### `GET /api/evidence`

List evidence visible to the caller.

**Query parameters:** `investigation_id`, `file_type`, `status`, `search`, `limit`, `offset`.

### `GET /api/evidence/{evidence_id}`

Evidence metadata, metadata extraction result, custody events, and analysis results.

**Response `200`** — the evidence object plus:

```json
{
  "chain_of_custody": [
    {
      "id": "...",
      "event_type": "upload",
      "actor_id": "3f8a1c2e-...",
      "actor_name": "Jane Investigator",
      "timestamp": "2026-11-13T09:42:11.204Z",
      "details": "Original stored, SHA-256 verified."
    }
  ],
  "analysis_results": [ /* analysis objects */ ]
}
```

### `GET /api/evidence/{evidence_id}/download`

Returns the **original** file via a short-lived signed URL. Access is authorised and
recorded as a chain-of-custody `access` event.

**Response `200`**

```json
{ "url": "https://<project>.supabase.co/storage/v1/object/sign/evidence-originals/...?token=...", "expires_in": 300 }
```

### `POST /api/evidence/{evidence_id}/integrity-check`

Re-read the stored object, recompute SHA-256, and compare against the recorded hash.

**Response `200`**

```json
{
  "evidence_id": "7c1e2a3b-...",
  "recorded_hash": "e3b0c442...",
  "computed_hash": "e3b0c442...",
  "integrity_verified": true,
  "verified_at": "2026-11-13T09:45:02.117Z"
}
```

**Response `409`** — `EVIDENCE_INTEGRITY_FAILED` when the hashes differ. The discrepancy
is written to `audit_logs` as a high-severity event.

---

## 6. Forensic Analysis Endpoints

All four share the same contract.

**Request body**

```json
{ "evidence_id": "7c1e2a3b-4d5e-6f70-8192-a3b4c5d6e7f8", "options": {} }
```

**Response `202`**

```json
{
  "analysis_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "evidence_id": "7c1e2a3b-...",
  "module": "deeptrace",
  "status": "pending",
  "poll_url": "/api/analysis/c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f/status"
}
```

**Errors:** `403` not authorised for this evidence · `404` evidence missing ·
`409` analysis already running for this evidence and module · `415` file type not
supported by the module · `503` required engine or model unavailable.

### `POST /api/deeptrace/analyze`

Image and video forensics.

**Module-specific options**

```json
{
  "evidence_id": "...",
  "options": {
    "frame_interval_seconds": 1.0,
    "max_frames": 500,
    "run_ela": true,
    "deepfake_model": null
  }
}
```

`deepfake_model: null` means no calibrated model is available. The result then contains
only heuristic observations, each tagged `method: "heuristic"`, and
`deepfake_assessment.status = "unavailable"`.

**Result payload (`result_data`)**

```json
{
  "file_type": "video",
  "metadata": {
    "width": 1920, "height": 1080, "duration_seconds": 94.3,
    "codec": "h264", "frame_rate": 30.0, "exif": { "make": "...", "model": "..." }
  },
  "frames": [
    { "index": 0, "timestamp": 0.0, "storage_path": "evidence-derived/.../frames/000000.jpg" },
    { "index": 30, "timestamp": 1.0, "storage_path": "evidence-derived/.../frames/000030.jpg" }
  ],
  "findings": [
    { "label": "Metadata", "value": "Standard EXIF present", "status": "info", "method": "heuristic", "confidence": null },
    { "label": "ELA compression variance", "value": "Elevated variance in regions 12-40", "status": "warning", "method": "heuristic", "confidence": null },
    { "label": "Deepfake model", "value": "Not configured", "status": "info", "method": "model", "confidence": null }
  ],
  "deepfake_assessment": {
    "status": "unavailable",
    "reason": "No calibrated deepfake model is configured for this deployment.",
    "is_model_prediction": false
  },
  "explanation": "AI-written summary grounded in the findings above.",
  "limitations": [
    "Heuristic checks do not establish synthetic origin.",
    "Absence of a model result is not evidence of authenticity."
  ]
}
```

### `POST /api/spytrace/analyze`

Android APK static analysis.

```json
{ "evidence_id": "...", "options": { "extract_urls": true, "extract_strings": true } }
```

```json
{
  "file_type": "apk",
  "metadata": {
    "package_name": "com.example.tracker",
    "version_name": "2.1.4",
    "sdk_min": 21, "sdk_target": 33,
    "main_activity": "com.example.tracker.MainActivity",
    "is_signed": true
  },
  "permissions": [
    { "name": "android.permission.READ_SMS", "sensitive": true, "protection": "dangerous" },
    { "name": "android.permission.INTERNET", "sensitive": false, "protection": "normal" }
  ],
  "suspicious_combinations": [
    {
      "permissions": ["READ_SMS", "SEND_SMS", "INTERNET"],
      "indicator": "SMS read/send combined with network access permits silent exfiltration.",
      "severity": "high",
      "is_heuristic": true
    }
  ],
  "services": ["com.example.tracker.BackgroundService"],
  "receivers": ["com.example.tracker.BootReceiver"],
  "activities": ["com.example.tracker.MainActivity"],
  "domains": ["analytics.tracker-cdn.example", "cmd.tracker-c2.example"],
  "risk_indicators": [
    { "label": "Background persistence", "evidence": "BootReceiver registered for BOOT_COMPLETED", "severity": "medium" }
  ],
  "risk_classification": { "level": "high", "score": 0.72, "is_heuristic": true },
  "limitations": [
    "Static analysis only — the APK was never executed.",
    "Sensitive permissions do not by themselves indicate spyware.",
    "Obfuscated or dynamically loaded code may be missed."
  ]
}
```

### `POST /api/voiceproof/analyze`

Audio forensics.

```json
{ "evidence_id": "...", "options": { "synthetic_voice_model": null, "segment_seconds": 5 } }
```

```json
{
  "file_type": "audio",
  "metadata": {
    "duration_seconds": 134.2, "sample_rate": 44100, "channels": 2,
    "codec": "pcm_s16le", "format": "wav"
  },
  "waveform_path": "evidence-derived/.../waveform.png",
  "spectrogram_path": "evidence-derived/.../spectrogram.png",
  "features": { "peak_dbfs": -1.2, "clipping_ratio": 0.0003, "silence_ratio": 0.061, "spectral_centroid_mean": 2143.7 },
  "anomalies": [
    { "label": "Clipping", "start": 42.1, "end": 42.4, "severity": "low", "method": "heuristic" },
    { "label": "Abrupt spectral discontinuity", "start": 88.0, "end": 89.2, "severity": "medium", "method": "heuristic" }
  ],
  "synthetic_voice": {
    "status": "inconclusive",
    "is_model_prediction": true,
    "confidence": 0.41,
    "model_version": "synth-audio-v3",
    "segments": [ { "start": 88.0, "end": 89.2, "confidence": 0.63 } ]
  },
  "limitations": [
    "This module does not identify a speaker's real-world identity.",
    "Synthetic voice detection is not conclusive proof.",
    "Low confidence results should be treated as inconclusive."
  ]
}
```

### `POST /api/cybersleuth/analyze`

Digital artefact extraction and reconstruction.

```json
{ "evidence_id": "...", "options": { "max_records": 50000, "build_graph": true } }
```

```json
{
  "file_type": "json",
  "metadata": { "record_count": 12483, "format": "chat_export" },
  "timestamps": [
    { "raw": "12/03/2026 14:22:01", "normalized": "2026-03-12T14:22:01Z", "source": "field.timestamp" }
  ],
  "entities": [
    { "text": "John Smith", "type": "PERSON", "source": "field.sender", "occurrence_count": 148 },
    { "text": "192.168.1.44", "type": "IP_ADDRESS", "source": "field.metadata", "occurrence_count": 3 }
  ],
  "urls": ["https://cdn.example.com/upload"],
  "domains": ["cdn.example.com"],
  "emails": ["john@example.com"],
  "phones": ["+1-202-555-0147"],
  "duplicates": [ { "record_id": "8821", "duplicate_of": "8819", "reason": "identical payload" } ],
  "messages": [ { "group": "2026-03-12", "count": 214, "participants": ["John Smith", "Jane Doe"] } ],
  "classified_events": [ { "timestamp": "2026-03-12T14:22:01Z", "event_type": "file_transfer", "confidence": 0.79 } ],
  "timeline": [ { "timestamp": "2026-03-12T14:22:01Z", "event_type": "file_transfer", "source_file": "chat_export.json", "extracted_content": "document.pdf uploaded", "entities": ["John Smith"], "evidence_id": "7c1e2a3b-..." } ],
  "graph": {
    "nodes": [ { "id": "e1", "label": "John Smith", "type": "entity" }, { "id": "ev1", "label": "chat_export.json", "type": "evidence" } ],
    "edges": [ { "source": "ev1", "target": "e1", "relation": "mentions", "weight": 148 } ]
  },
  "deletion_reconstruction": {
    "attempted": false,
    "reason": "No recoverable source artefact was available. No content was reconstructed."
  }
}
```

---

## 7. Analysis Status

### `GET /api/analysis/{analysis_id}/status`

Poll a background analysis.

**Response `200`**

```json
{
  "analysis_id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f",
  "evidence_id": "7c1e2a3b-...",
  "module": "deeptrace",
  "status": "completed",
  "confidence_score": null,
  "error_message": null,
  "created_at": "2026-11-13T09:42:11.204Z",
  "completed_at": "2026-11-13T09:42:48.913Z",
  "result_data": { /* module payload */ }
}
```

`status` is one of `pending`, `running`, `completed`, `failed`.

**Response `200` (failed)**

```json
{
  "analysis_id": "...",
  "status": "failed",
  "error_message": "Model weights not available for the requested model id.",
  "confidence_score": null
}
```

---

## 8. Correlation Engine

### `POST /api/correlation/{investigation_id}`

Run correlation across every completed analysis in the investigation.

**Response `200`**

```json
{
  "investigation_id": "9b2d4e6a-...",
  "generated_at": "2026-11-13T09:50:00.000Z",
  "statistics": { "evidence_items": 7, "modules_involved": 4, "correlations": 12, "timeline_events": 86 },
  "timeline": [
    {
      "timestamp": "2026-03-12T14:22:01Z",
      "event_type": "file_transfer",
      "source_evidence_id": "7c1e2a3b-...",
      "source_file": "chat_export.json",
      "module": "cybersleuth",
      "extracted_content": "document.pdf uploaded",
      "entities": ["John Smith"]
    }
  ],
  "correlations": [
    {
      "id": "d1e2f3a4-...",
      "source_evidence_id": "aa11...",
      "target_evidence_id": "bb22...",
      "finding_id": "cc33...",
      "correlation_type": "temporal",
      "reason": "Video frame timestamp 2026-03-12T14:22:03Z falls within 2.0s of the chat message timestamp.",
      "supporting_data": { "video_timestamp": "2026-03-12T14:22:03Z", "message_timestamp": "2026-03-12T14:22:01Z", "delta_seconds": 2.0 },
      "timestamp": "2026-03-12T14:22:01Z",
      "confidence": 0.92,
      "verified": false,
      "is_hypothesis": true,
      "explanation": "AI-written explanation referencing only the evidence IDs above."
    }
  ],
  "graph": {
    "nodes": [ { "id": "aa11...", "label": "surveillance_footage.mp4", "type": "evidence", "module": "deeptrace" } ],
    "edges": [ { "source": "aa11...", "target": "bb22...", "type": "temporal", "confidence": 0.92 } ]
  },
  "limitations": [
    "Correlations are hypotheses generated from structural signals, not conclusions.",
    "Timestamp proximity does not establish causation or identity.",
    "Every correlation requires investigator verification before being relied upon."
  ]
}
```

### `GET /api/correlation/{investigation_id}`

Fetch the most recent stored correlation result without recomputing.

### `PATCH /api/correlation/{investigation_id}/correlations/{correlation_id}`

Investigator verification.

```json
{ "verified": true, "investigator_note": "Confirmed — both artefacts originate from the same device." }
```

**Response `200`** — the updated correlation, with `verified` and the note recorded.

---

## 9. Reports

### `POST /api/reports/{investigation_id}`

Generate a PDF forensic report.

**Response `202`**

```json
{
  "report_id": "f1e2d3c4-b5a6-4978-8a9b-0c1d2e3f4a5b",
  "investigation_id": "9b2d4e6a-...",
  "status": "generating"
}
```

### `GET /api/reports/{id}`

Fetch report metadata.

```json
{
  "id": "f1e2d3c4-...",
  "investigation_id": "9b2d4e6a-...",
  "title": "Forensic Report — CASE-2026-001",
  "status": "ready",
  "generated_by": "3f8a1c2e-...",
  "generated_at": "2026-11-13T09:55:00.000Z",
  "download_url": "https://<project>.supabase.co/storage/v1/object/sign/reports/...?token=...",
  "sections": [
    "investigation_details",
    "evidence_inventory",
    "chain_of_custody",
    "deeptrace_findings",
    "spytrace_findings",
    "voiceproof_findings",
    "cybersleuth_findings",
    "correlation_timeline",
    "relationship_graph",
    "ai_summary",
    "limitations",
    "investigator_review"
  ]
}
```

### `GET /api/reports/{id}/download`

Streams the generated PDF (or redirects to a short-lived signed URL).

The generated report **must** contain a limitations section stating that it is an
investigative aid and not a court-certified or legally conclusive document.

---

## 10. Audit Logs

### `GET /api/audit-logs`

List audit entries.

**Query parameters:** `action`, `resource`, `user_id`, `investigation_id`, `evidence_id`,
`from`, `to`, `limit`, `offset`.

**Response `200`**

```json
{
  "items": [
    {
      "id": "7a8b9c0d-1e2f-4a3b-8c9d-0e1f2a3b4c5d",
      "user_id": "3f8a1c2e-...",
      "user_name": "Jane Investigator",
      "action": "evidence.upload",
      "resource": "evidence",
      "resource_id": "7c1e2a3b-...",
      "ip_address": "203.0.113.42",
      "details": { "filename": "surveillance_footage.mp4", "sha256": "e3b0c442..." },
      "timestamp": "2026-11-13T09:42:11.204Z"
    }
  ],
  "total": 1
}
```

Audit rows are write-once. No update or delete policy is granted to any role.

---

## 11. Error Codes

| Code | Status | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request body failed schema validation |
| `UNAUTHENTICATED` | 401 | Missing or invalid access token |
| `FORBIDDEN` | 403 | Authenticated but not permitted |
| `NOT_FOUND` | 404 | Resource missing or not visible |
| `DUPLICATE_CASE_ID` | 409 | `case_id` already exists |
| `ANALYSIS_IN_PROGRESS` | 409 | An analysis for this evidence and module is already running |
| `EVIDENCE_INTEGRITY_FAILED` | 409 | Recomputed hash differs from the recorded hash |
| `FILE_TOO_LARGE` | 413 | Upload exceeds `MAX_UPLOAD_SIZE_MB` |
| `UNSUPPORTED_FILE_TYPE` | 415 | Extension not in `ALLOWED_EXTENSIONS` |
| `RATE_LIMITED` | 429 | Too many requests |
| `AI_SERVICE_UNAVAILABLE` | 503 | Gemini key missing or the model call failed |
| `ENGINE_UNAVAILABLE` | 503 | A forensic dependency is not installed |
| `EVIDENCE_CORRUPTED` | 500 | Post-upload hash verification failed |

---

## 12. Rate Limits

| Endpoint | Limit |
|---|---|
| `POST /api/auth/login` | 5 / minute / IP |
| `POST /api/auth/register` | 3 / minute / IP |
| `POST /api/auth/reset-password` | 3 / minute / IP |
| `POST /api/evidence/upload` | 10 / minute / user |
| `POST /api/*/analyze` | 20 / minute / user |
| `POST /api/reports/{id}` | 5 / minute / user |
| `POST /api/correlation/{id}` | 5 / minute / user |

Exceeding a limit returns `429` with a `Retry-After` header.
