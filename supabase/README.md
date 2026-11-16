# Supabase — Database Schema & Migrations

> **Status: implemented.** Twelve migrations exist in `migrations/`. They are the
> single source of truth for the CyberSleuth AI data model and are applied both
> to the embedded local PostgreSQL and to a hosted Supabase project.

---

## Migration files

Applied in filename order. Each file is self-contained and idempotent enough to
be re-applied safely.

| File | Purpose |
|---|---|
| `000_auth_parity.sql` | Creates the `auth` schema parity shim: a local `auth.users` table plus `auth.uid()`, `auth.role()` and `auth.email()` on plain PostgreSQL, where GoTrue does not exist. |
| `001_extensions_and_functions.sql` | Best-effort `pgcrypto` / `uuid-ossp`, the request-identity helpers (`request_claims`, `set_request_identity`, `current_user_id`, `current_user_role`, `is_supervisor`) and the access helpers `can_access_investigation()` / `can_manage_investigation()`. |
| `002_profiles.sql` | The `profiles` table plus the `handle_new_user()` / `handle_user_update()` triggers that keep it in step with `auth.users`. |
| `003_investigations.sql` | `investigations` and `investigation_members`, the trigger that enrols the owner as a lead member, and `touch_updated_at()`. |
| `004_evidence.sql` | `evidence`, `evidence_events` and the tamper-evident `chain_of_custody` ledger, with triggers that block edits to originals and to the ledger. |
| `005_analysis_results.sql` | `analysis_results` and `forensic_timelines` — the structured output of one forensic module run. |
| `006_correlation_and_reports.sql` | `correlation_results` and `generated_reports` (rendered PDFs with their hash). |
| `007_audit_logs.sql` | The write-once `audit_logs` trail and the trigger that refuses updates and deletes. |
| `008_rls_policies.sql` | Row Level Security on every table, the per-table policies, and the restricted `cybersleuth_app` role with its grants. |
| `009_storage_buckets.sql` | The private buckets `evidence-originals`, `evidence-derived` and `reports` plus the `storage.objects` policies (exception safe: a platform-owned storage schema produces a NOTICE, never a failed migration). |
| `010_indexes.sql` | An index for every column used by a policy or a common query. |
| `011_investigations_returning.sql` | The `is_investigation_member()` helper and a rewritten `investigations_select` policy, so that `INSERT ... RETURNING` is not rejected by the SELECT policy. |
| `012_security_and_analysis_fixes.sql` | Adds the `unavailable` analysis status, widens `profiles_select` to colleagues who share an investigation, allows anonymous audit rows, re-scopes the `auth.users` grants to individual columns and adds the membership index the widened policy needs. |

---

## The eleven tables

`profiles` · `investigations` · `investigation_members` · `evidence` ·
`analysis_results` · `evidence_events` · `forensic_timelines` · `chain_of_custody` ·
`generated_reports` · `audit_logs` · `correlation_results`

All use UUID primary keys, foreign keys, timestamps, and RLS. See
`../docs/ARCHITECTURE.md` § 3 for the full data model and relationship diagram.

---

## The auth-parity shim

On Supabase the `auth` schema and the `auth.users` table are owned by GoTrue and
are managed by the platform. On a standalone PostgreSQL instance they do not
exist at all.

`000_auth_parity.sql` closes that gap: it creates a compatible subset of
`auth.users` (with the columns the application needs: `id`, `email`,
`encrypted_password`, `email_confirmed_at`, `raw_user_meta_data`, `is_active`,
`created_at`, `updated_at`) and the three identity helpers `auth.uid()`,
`auth.role()` and `auth.email()`. Every statement is guarded, so the file is
safe to run against Supabase — where the platform's own objects simply win.

The result is that **one set of SQL policies works in both environments**:

* Locally the API publishes the caller identity through
  `public.set_request_identity()`, which sets the `app.user_id`,
  `app.user_role` and `app.user_email` GUCs for the transaction.
* On Supabase the identity arrives in the `request.jwt.claims` GUC.
* `public.request_claims()` understands both, and `public.current_user_id()`,
  `public.current_user_role()` and `public.is_supervisor()` read from it.

Every RLS policy in `008_rls_policies.sql` is written against those helpers and
never against `auth.uid()` directly, so the policy text is identical in both
environments.

---

## Applying the migrations

### The application applies them for you

`backend/app/database/migrator.py` discovers every `*.sql` file in this
directory, applies the pending ones in filename order and records each one in
`public.schema_migrations`, so an interrupted run resumes where it stopped.
The API runs the migrator on start-up, before serving traffic. The **same
files** are used against the embedded local PostgreSQL
(`backend/app/database/local_postgres.py`) and against a hosted project — there
is no second, divergent copy of the schema.

### Manually, with psql

`supabase db push` is deliberately **not** used: the Supabase CLI only accepts
migrations named `<timestamp>_<name>.sql`, and these files are numbered
(`000_…` – `012_…`) because the migrator, the tests and the tooling reference
them by name. Renaming them would break that. Apply them with `psql` instead:

```bash
# bash / Git Bash / WSL
for f in supabase/migrations/*.sql; do
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f" || exit 1
done
```

```powershell
# PowerShell
Get-ChildItem supabase/migrations/*.sql | Sort-Object Name | ForEach-Object {
    psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Migration failed: $($_.Name)" }
}
```

`ON_ERROR_STOP=1` matters: without it `psql` keeps going after an error and a
half-applied migration is very hard to diagnose.

For a hosted project, run the same loop against the Supabase connection string
with the `postgres` role. `supabase/config.toml` is provided so the CLI can
link to the project and so `supabase start` / `supabase db reset` find a valid
configuration; `supabase/seed.sql` is an intentional no-op, because the demo
data is seeded through the live API by `python scripts/seed_demo_data.py`.

---

## Storage buckets

| Bucket | Contents | Policy |
|---|---|---|
| `evidence-originals` | Uploaded originals, byte-identical | **No UPDATE policy** — immutable |
| `evidence-derived` | Frames, thumbnails, waveforms, spectrograms | Processing pipeline only |
| `reports` | Rendered PDF reports | Report service only |

All three are **private**. Downloads use short-lived signed URLs.
