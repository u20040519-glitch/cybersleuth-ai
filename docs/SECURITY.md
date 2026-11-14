# CyberSleuth AI — Security

> Threat model, controls, and secure-development rules for the CyberSleuth AI platform.

This document covers what is implemented today (Phase 1), what is deliberately deferred
to later phases, and the rules that must not be broken when those phases land.

---

## 1. Scope

CyberSleuth AI processes **evidence from real investigations**: surveillance footage,
recorded audio, mobile applications, chat exports, and logs. A compromise of this
platform is not merely a data breach — it would corrupt the evidentiary record of
active cases. Security is therefore a **correctness** requirement, not just an
operational nicety.

### 1.1 Assets

| Asset | Sensitivity | Primary control |
|---|---|---|
| Evidence originals | **Critical** — irreplaceable, may be the subject of legal proceedings | Immutable storage, SHA-256, chain of custody |
| Chain-of-custody ledger | **Critical** — its integrity is the basis of evidentiary admissibility | Append-only, audit-logged |
| User credentials | High | Supabase Auth, Argon2id/bcrypt via Supabase, httpOnly session handling |
| Supabase service-role key | **Critical** — bypasses RLS entirely | Backend-only, never in the frontend bundle |
| Gemini API key | High — billable and data-adjacent | Backend-only, never in the frontend bundle |
| PII inside evidence | High | RLS, private storage, minimal retention |
| Forensic findings | Medium-high — false conclusions can cause real harm | Epistemic labelling, investigator verification |

---

## 2. Threat Model

| # | Threat | Impact | Mitigation | Phase |
|---|---|---|---|---|
| T1 | **Secrets leaked into the frontend bundle** | Full account/DB compromise | Strict env var separation; only `VITE_*` public vars reach the browser; CI grep for key patterns | 1 / 2 |
| T2 | **Cross-tenant data access** | One investigator reads another's case | RLS on every table + server-side authorisation on every resource | 2 |
| T3 | **Evidence tampering after upload** | Loss of evidentiary integrity, case dismissal | Original bucket is immutable; SHA-256 verified before *and* after storage; integrity-check endpoint | 2 / 3 |
| T4 | **Service-role RLS bypass abused** | Authorisation checks silently skipped | Backend re-verifies the caller's authorisation on every resource, because service role bypasses RLS | 2 |
| T5 | **Malicious file upload** (huge file, zip bomb, traversal filename, crafted parser input) | DoS, path traversal, RCE | Extension + size allowlist, UUID-only storage paths, sanitised display names, patched parsers, size caps | 3 |
| T6 | **Executing an uploaded APK** | Host compromise | Static analysis only; explicit prohibition on execution | 4 |
| T7 | **Gemini inventing evidence** | False forensic conclusions, misdirected investigations | Grounded prompt with structured findings only; new facts forbidden; epistemic labelling; investigator verification | 5 |
| T8 | **AI output mistaken for a verdict** | Legal/ethical harm | UI separates observation / prediction / explanation / hypothesis; limitations on every result and report | 1 / 5 / 6 |
| T9 | **Prompt injection via uploaded content** | Model manipulation | Evidence content passed as inert data, never as instructions; instruction/evidence separation in the prompt; output schema validation | 5 |
| T10 | **CORS misconfiguration** | Cross-origin credential theft | Explicit origin allowlist; credentials not shared across origins | 2 |
| T11 | **Audit log tampering** | Inability to prove who did what | Write-once audit tables; no UPDATE/DELETE policy for any role | 2 |
| T12 | **Brute force / credential stuffing** | Account takeover | Rate limiting, Supabase built-in protections, email confirmation, MFA | 2 |
| T13 | **Report treated as court-certified** | Legal misrepresentation | Explicit non-certification statement in the report and UI | 6 |
| T14 | **Dependency compromise** | Supply-chain breach | Pinned versions, `npm audit` / `pip-audit` in CI, minimal dependency set | Ongoing |
| T15 | **IDOR on investigation/evidence IDs** | Data leakage via guessed UUIDs | Server-side authorisation on every lookup; `404` instead of `403` to avoid existence leakage | 2 |

---

## 3. Secret Management

### 3.1 The rule

> **If a value ends up in the browser bundle, it is public.**

Vite inlines every `VITE_`-prefixed variable into the JavaScript served to the browser.
A `GEMINI_API_KEY` in a `VITE_` variable is compromised the moment the page loads.

### 3.2 Variable classification

| Variable | Visibility | Where it lives |
|---|---|---|
| `VITE_SUPABASE_URL` | Public | `frontend/.env` |
| `VITE_SUPABASE_ANON_KEY` | Public (RLS-protected) | `frontend/.env` |
| `VITE_API_BASE_URL` | Public | `frontend/.env` |
| `SUPABASE_URL` | Server | `backend/.env` |
| `SUPABASE_ANON_KEY` | Server | `backend/.env` |
| `SUPABASE_SERVICE_ROLE_KEY` | **Server only — critical** | `backend/.env` |
| `GEMINI_API_KEY` | **Server only — critical** | `backend/.env` |
| `APP_SECRET_KEY` | **Server only** | `backend/.env` |
| `FRONTEND_URL` / `CORS_ORIGINS` | Server | `backend/.env` |

### 3.3 Controls

- `.env` is in `.gitignore` and **must never be committed**. `.env.example` files
  contain placeholders only.
- CI runs a secret scan on every push. Any match for a Supabase service-role key
  pattern (`sb_secret_...`) or a Gemini key pattern (`AIza...`) fails the build.
- No real credentials appear in source code, documentation, commit messages, generated
  prompts, or issue trackers.
- If a key is ever exposed, treat it as compromised: rotate it immediately at the
  provider, then update local `.env` files.

---

## 4. Authentication & Authorisation

### 4.1 Authentication

Supabase Auth issues a short-lived JWT. The backend verifies the signature against
Supabase on every protected request. The raw token is never written to `localStorage`.

### 4.2 Authorisation

**Frontend hiding is never authorisation.** Every protected page, plus every backend
route, performs its own check. The layered model:

```
1. Page level     ProtectedRoute blocks unauthenticated rendering (UX only)
2. Route level    require_auth() rejects requests without a valid token        → 401
3. Resource level require_case_access(case_id) checks ownership/membership     → 403 / 404
4. Row level      RLS policies enforce the same rule inside Postgres
```

Layers 2–4 are the security boundary. Layer 1 is a convenience.

### 4.3 The service-role caveat

The backend uses the Supabase **service role** for privileged writes (creating
analysis rows, writing to private buckets, appending to the audit ledger). The service
role **bypasses RLS entirely**. Therefore:

> **The backend must explicitly verify that the authenticated user is permitted to
> access each requested resource.** RLS alone is not a sufficient control in the
> service-role path — it is simply not evaluated.

This is enforced in `app/security/authorisation.py`, called from every route handler
that touches a user-owned resource.

### 4.4 Role model

| Capability | Investigator | Supervisor |
|---|---|---|
| Create investigations | Yes | Yes |
| Upload / manage evidence | Yes | Yes |
| Run forensic analysis | Yes | Yes |
| View findings | Own + assigned | Assigned + all owned |
| Generate reports | Yes | Yes |
| Review / approve findings | No | Yes |
| View audit logs | Own actions | All authorised investigations |
| Manage member access | Own investigations | Any authorised investigation |

---

## 5. Evidence Integrity

### 5.1 Immutability

The uploaded original is **never modified and never overwritten**. The
`evidence-originals` bucket has no UPDATE policy — only INSERT and SELECT (via signed
URL). Processed artefacts are written to a **separate** `evidence-derived` bucket.

### 5.2 Hash verification

```
upload bytes ──► compute SHA-256 ──► store original ──► re-read stored bytes
                                                              │
                                                   recompute SHA-256
                                                              │
                                                     compare ──┴──► mismatch → 500
```

Verification happens **before** storage (to record the authoritative hash) and
**after** storage (to detect corruption in transit or at rest). The
`POST /api/evidence/{id}/integrity-check` endpoint repeats this on demand, and a
mismatch raises a high-severity audit event.

### 5.3 Chain of custody

Every custody event is **append-only** and records: event type, actor, timestamp, and
details. Event types: `upload`, `access`, `process`, `export`, `share`. Custody rows
are never updated or deleted — a correction is recorded as a new event.

### 5.4 Storage access

- All buckets are **private**.
- Downloads use **short-lived signed URLs** (default 300s TTL), never public links.
- Every download generates a custody `access` event and an audit entry.

---

## 6. File Upload Security

| Control | Implementation |
|---|---|
| Extension allowlist | `ALLOWED_EXTENSIONS`; anything else → `415` |
| Size limit | `MAX_UPLOAD_SIZE_MB`; exceeded → `413` |
| Path traversal | Storage paths are built from **UUIDs only**; the original filename is never used to construct a path |
| Filename safety | The original name is preserved for fidelity but sanitised for display and storage |
| MIME validation | Detected from content, not trusted from the client header |
| Content sniffing | Magic-byte checks for common formats; extension/content mismatch is flagged |
| Storage location | Private bucket, separate path namespace per investigation |
| Parser isolation | Parsing runs in a worker with a time limit; a malformed file fails the job, not the host |
| No execution | Uploaded files are **never executed**. APK analysis is static only. |

> **Note on the current `.env`:** the pre-existing file still contains values from the
> earlier project, including a live Gemini key and SMTP credentials. Replace them with
> your own CyberSleuth AI values, and rotate any key that has been shared or committed.

---

## 7. AI Safety

### 7.1 Gemini is an explainer, not a detector

| Gemini **may** | Gemini **may not** |
|---|---|
| Summarise structured findings | Detect deepfakes |
| Explain a technical finding in plain language | Detect synthetic voice |
| Narrate a correlation that the engine produced | Classify malware or spyware |
| Draft report narrative from verified findings | Invent timestamps, entities, or evidence |
| Answer natural-language questions over findings | Infer a person's identity or guilt |
| Suggest what to investigate next | Replace investigator verification |

**Detection is done by deterministic forensic engines or calibrated models with a
recorded version and confidence.** If no calibrated model is configured, the response
is `status: "unavailable"` with a reason — never a fabricated confidence score.

### 7.2 Grounding

The Gemini request contains only the serialised structured findings and correlation
records — never raw file bytes. The prompt instructs the model to reference only
evidence IDs present in the input and to mark uncertainty explicitly. The response is
validated against a schema; anything referencing an unknown evidence ID is rejected
and logged.

### 7.3 Prompt injection resistance

Uploaded content is **data, never instruction**. Concretely:

- File content is wrapped in a delimited block and explicitly labelled as untrusted
  content that must not be treated as instructions.
- System-level instructions are fixed and not influenced by file content.
- The model output is parsed against a strict schema, so injected text cannot change
  the response shape.
- The Gemini key is server-side, so an injected instruction cannot reach a key.

### 7.4 Failure handling

Every Gemini call handles: invalid API key (`401` → `503 AI_SERVICE_UNAVAILABLE`),
rate limit (`429` → exponential backoff, then degrade gracefully), timeout
(`504` → `AI_SERVICE_UNAVAILABLE`), empty response, and model unavailability. A Gemini
failure **never** invalidates the forensic findings — it only removes the explanation
layer.

---

## 8. Forensic Integrity Rules

These are product rules, enforced in code review, not optional preferences.

1. **Never claim a deepfake from metadata alone.** Unusual metadata is a *heuristic
   observation*. A deepfake claim requires a calibrated model's prediction, with its
   version and confidence attached.
2. **Never label an app "spyware" because of permissions alone.** Sensitive permissions
   raise a *risk indicator*. Legitimate applications request the same permissions.
3. **Never identify a speaker.** VoiceProof AI detects synthetic-speech indicators. It
   does not identify who is speaking.
4. **Never fabricate deleted evidence.** Reconstruction is attempted only when genuine
   recoverable artefacts exist, and the output names the artefact it came from.
5. **Never infer identity or guilt from timestamps.** Correlations are hypotheses
   requiring investigator verification.
6. **Never present an AI-generated report as court-certified.** Every report carries an
   explicit non-certification statement.
7. **Never present demo data as findings.** Demo content is labelled and segregated.

---

## 9. Secure Development Rules

### 9.1 For the frontend

- Only `VITE_`-prefixed variables may be referenced. No exceptions, no "just for dev".
- Never store tokens in `localStorage` or `sessionStorage`.
- All user-supplied text rendered in the UI is escaped by React by default; never use
  `dangerouslySetInnerHTML` on evidence-derived content.
- Validate and sanitise file names and user input before display.
- No service-role key, no Gemini key, no Supabase secret in any client-side code path.

### 9.2 For the backend

- Validate every request with a Pydantic model. Never trust request bodies.
- Never log secrets, tokens, raw passwords, or full evidence contents.
- Redact sensitive fields in structured logging.
- Parameterise all database access — the Supabase client handles this, but avoid raw
  SQL string interpolation.
- Handle `IntegrityError` and race conditions explicitly on unique constraints.
- Set explicit timeouts on every outbound network call (Supabase, Gemini).
- Run the forensic engines in a worker with a hard time limit and memory cap.

### 9.3 For the database

- RLS enabled on **every** table. No exceptions.
- No `UPDATE` or `DELETE` policy on `chain_of_custody` or `audit_logs`.
- Foreign keys with explicit `ON DELETE` behaviour — prefer `RESTRICT` on evidentiary
  tables so evidence cannot be orphaned.
- Index every column used in a policy filter (`investigation_id`, `user_id`,
  `evidence_id`).
- Separate the `anon` and `service_role` usage: the frontend uses `anon`; the backend
  uses `service_role` only where RLS would otherwise block a legitimate write, and it
  re-checks authorisation itself.

### 9.4 CI gates

| Gate | Tool | Blocking |
|---|---|---|
| Type check | `tsc --noEmit` | Yes |
| Build | `vite build` | Yes |
| Lint | ESLint | Yes |
| Secret scan | custom grep + `gitleaks` | Yes |
| Backend tests | `pytest` | Yes |
| Dependency audit | `npm audit`, `pip-audit` | Advisory |

---

## 10. Incident Response

| Incident | Immediate action |
|---|---|
| Exposed Gemini key | Revoke in Google AI Studio, generate a new one, update `backend/.env`, redeploy |
| Exposed Supabase service-role key | Revoke in Supabase dashboard, rotate, audit `audit_logs` for the exposure window |
| Evidence integrity failure | Halt the investigation, preserve the object, escalate to the supervisor, never overwrite the affected file |
| Cross-tenant access discovered | Revoke sessions, audit `audit_logs` for the window, fix the RLS policy, add a regression test |
| Unauthorized evidence access | Export the audit trail, preserve it, notify the case supervisor and legal |

---

## 11. Current Security Posture

### Implemented in Phase 1

- Strict TypeScript (`strict`, `noUnusedLocals`, `noImplicitAny`, `noFallthroughCasesInSwitch`).
- Zero secrets in the frontend bundle — only public `VITE_` variables exist, and the
  `.env` files are gitignored with placeholder-only `.env.example` files.
- Client-side SHA-256 computation on upload (informational; the backend remains the
  verification authority).
- Backend-independent protected routes and guest routes.
- No `dangerouslySetInnerHTML` anywhere in the codebase.
- Explicit epistemic labelling in the UI — heuristic vs model vs AI explanation.
- Honest "Demo mode" labelling so sample data is never mistaken for findings.
- Explicit in-code prohibitions on executing uploaded APKs.

### Not yet implemented (Phases 2–7) — tracked as known gaps

- Supabase Auth and RLS are **not** wired; the Phase 1 auth context is a local demo
  implementation and is **not** a security control.
- There is no backend, so no server-side authorisation exists yet.
- File validation is client-side only; the server-side allowlist in
  `docs/API.md` is Phase 3.
- No rate limiting, audit persistence, or key rotation automation.
- No security headers or CSP (the Nginx/Vercel config in Phase 7 will add them).

> **Do not treat the Phase 1 build as deployable to production with real evidence.**
> It is a complete, functional UI awaiting its backend.
