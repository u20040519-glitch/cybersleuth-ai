# Supabase — Database Schema & Migrations

> **Status: Phase 2.** The schema below is the designed target. No migration files
> have been written yet.

This directory will hold the SQL migrations that create and secure the CyberSleuth AI
data model on Supabase PostgreSQL.

---

## Planned migration files

| File | Contents |
|---|---|
| `001_extensions_and_functions.sql` | `pgcrypto`, `uuid` generation, `can_access_investigation()` helper |
| `002_profiles.sql` | `profiles` table + `handle_new_user()` trigger on `auth.users` |
| `003_investigations.sql` | `investigations` + `investigation_members` |
| `004_evidence.sql` | `evidence`, `evidence_events`, `chain_of_custody` |
| `005_analysis_results.sql` | `analysis_results` + `forensic_timelines` |
| `006_correlation_and_reports.sql` | `correlation_results`, `generated_reports` |
| `007_audit_logs.sql` | `audit_logs` (write-once) |
| `008_rls_policies.sql` | RLS enabled on every table + policies |
| `009_storage_buckets.sql` | Private buckets `evidence-originals`, `evidence-derived`, `reports` |
| `010_indexes.sql` | Indexes on every policy filter column |

---

## The eleven tables

`profiles` · `investigations` · `investigation_members` · `evidence` ·
`analysis_results` · `evidence_events` · `forensic_timelines` · `chain_of_custody` ·
`generated_reports` · `audit_logs` · `correlation_results`

All use UUID primary keys, foreign keys, timestamps, and RLS. See
`../docs/ARCHITECTURE.md` § 3 for the full data model and relationship diagram.

---

## Applying migrations

```bash
# Supabase CLI
supabase link --project-ref <your-project-ref>
supabase db push

# or paste directly into the Supabase SQL editor
```

---

## Storage buckets

| Bucket | Contents | Policy |
|---|---|---|
| `evidence-originals` | Uploaded originals, byte-identical | **No UPDATE policy** — immutable |
| `evidence-derived` | Frames, thumbnails, waveforms, spectrograms | Processing pipeline only |
| `reports` | Rendered PDF reports | Report service only |

All three are **private**. Downloads use short-lived signed URLs.
