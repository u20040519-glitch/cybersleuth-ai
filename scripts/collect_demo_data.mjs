// =============================================================================
// CYBERSLEUTH AI - Collect the demo snapshot
// =============================================================================
// Packs the seeded case (investigations, evidence, module results, correlation,
// reports, audit logs) into the frontend, so the published demo can run
// without the backend. Everything is read through the live API; nothing is
// invented.
//
// Usage:
//   node scripts/collect_demo_data.mjs
// =============================================================================

import { execFileSync } from 'node:child_process'
import { writeFile, mkdir, readFile, copyFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const API = process.env.CYBERSLEUTH_API || 'http://127.0.0.1:8000/api'
// The storage backend keeps evidence under backend/storage/evidence-originals.
const storageRoot = join(repoRoot, 'backend', 'storage', 'evidence-originals')

const [investigatorEmail, investigatorPassword] = ['investigator@cybersleuth.ai', 'Investigator!2026']

function request(path, { token, method = 'GET', body } = {}) {
  const args = ['-s', '-m', '120', '-X', method, `${API}${path}`, '-H', 'Content-Type: application/json']
  if (token) args.push('-H', `Authorization: Bearer ${token}`)
  if (body) args.push('-d', JSON.stringify(body))
  const out = execFileSync(process.platform === 'win32' ? 'curl.exe' : 'curl', args, {
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  })
  return out ? JSON.parse(out) : null
}

console.log(`Signing in as ${investigatorEmail} ...`)
const session = request('/auth/login', { method: 'POST', body: { email: investigatorEmail, password: investigatorPassword } })
const token = session.access_token

console.log('Collecting investigations ...')
const investigations = request('/investigations', { token })

const snapshot = {
  investigations: {},
  evidence: {},
  analysisResults: [],
  correlations: {},
  reports: [],
  auditLogs: [],
  dashboard: null,
  members: {},
  custody: {},
  custodyVerification: {},
  events: {},
  integrityChecks: {},
}

for (const investigation of investigations) {
  console.log(`  case ${investigation.case_id} ...`)
  const detail = request(`/investigations/${investigation.id}`, { token })
  snapshot.investigations[investigation.id] = detail
  snapshot.members[investigation.id] = request(`/investigations/${investigation.id}/members`, { token })

  const evidence = request(`/evidence?investigation_id=${investigation.id}`, { token })
  snapshot.evidence[investigation.id] = evidence

  // Analyses for every evidence item of this case
  const results = request(`/analysis/results?investigation_id=${investigation.id}&limit=500`, { token })
  snapshot.analysisResults.push(...results)

  snapshot.correlations[investigation.id] = request(`/correlation/${investigation.id}`, { token })
}

// Dedupe (the list endpoint returns every report for the case on each call).
const uniqueReports = new Map()
for (const investigation of investigations) {
  for (const report of request(`/reports?investigation_id=${investigation.id}`, { token })) {
    uniqueReports.set(report.id, report)
  }
}
snapshot.reports = [...uniqueReports.values()]

// Custody ledger, events and integrity state for every evidence item.
for (const item of Object.values(snapshot.evidence).flat()) {
  snapshot.custody[item.id] = request(`/evidence/${item.id}/custody`, { token })
  snapshot.custodyVerification[item.id] = request(`/evidence/${item.id}/custody/verify`, { token })
  snapshot.events[item.id] = request(`/evidence/${item.id}/events`, { token })
  snapshot.integrityChecks[item.id] = request(`/evidence/${item.id}/integrity-check`, { method: 'POST', token })
}

console.log('Collecting audit logs ...')
snapshot.auditLogs = request('/audit-logs?limit=200', { token })

console.log('Collecting dashboard ...')
snapshot.dashboard = request('/dashboard/stats', { token })

// Evidence files (so downloads and integrity checks work in the demo).
const targetDir = join(repoRoot, 'frontend', 'public', 'demo', 'files')
await mkdir(targetDir, { recursive: true })

// Storage keys are <sha>-<original filename>; keep the mapping by sha256.
const shaToKey = new Map()
for (const evidence of Object.values(snapshot.evidence).flat()) {
  shaToKey.set(evidence.sha256_hash, { id: evidence.id, key: evidence.storage_path })
}

for (const item of [...shaToKey.values()]) {
  const fileName = String(item.key).split(/[\\/]/).pop()
  let src = null
  const search = async (dir) => {
    const { readdirSync, statSync } = await import('node:fs')
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name)
      if (entry.isDirectory()) await search(full)
      else if (entry.name === fileName) src = full
    }
  }
  if (existsSync(storageRoot)) await search(storageRoot)
  if (src) {
    await copyFile(src, join(targetDir, fileName))
    snapshot.files = snapshot.files || {}
    snapshot.files[item.id] = `demo/files/${fileName}`
  }
}

// Reports (the generated PDFs).
const reportsDir = join(repoRoot, 'frontend', 'public', 'demo', 'reports')
await mkdir(reportsDir, { recursive: true })
const reportsStorageRoot = join(repoRoot, 'backend', 'storage', 'reports')

for (const report of snapshot.reports) {
  if (!report.storage_path) continue
  const fileName = String(report.sha256_hash || report.id) + '.pdf'
  const search = async (dir) => {
    const { readdirSync } = await import('node:fs')
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name)
      if (entry.isDirectory()) await search(full)
      else if (entry.name === String(report.storage_path).split(/[\\/]/).pop()) {
        await copyFile(full, join(reportsDir, fileName))
        report.demoFile = `demo/reports/${fileName}`
      }
    }
  }
  if (existsSync(reportsStorageRoot)) await search(reportsStorageRoot)
}

const output = `// =============================================================================
// CYBERSLEUTH AI - Demo snapshot
// =============================================================================
// Generated by scripts/collect_demo_data.mjs from the live seeded case.
// Used by the static demo build (VITE_DEMO_MODE=true): the published demo
// needs no backend, no tunnel and no account.
// =============================================================================

export const DEMO = ${JSON.stringify(snapshot, null, 2)} as const
`

// Never leak the collecting machine's profile path into the demo snapshot.
const redacted = output.replace(/[A-Za-z]:\\\\Users\\\\[^\\\\"']+(?=\\\\|\\\\)/g, 'C:\\\\Users\\\\<user>')

const outputPath = join(repoRoot, 'frontend', 'src', 'services', 'demo', 'data.ts')
await mkdir(join(repoRoot, 'frontend', 'src', 'services', 'demo'), { recursive: true })
await writeFile(outputPath, redacted, 'utf8')

console.log(`Wrote ${join(repoRoot, 'frontend', 'src', 'services', 'demo', 'data.ts')}`)
console.log(`investigations: ${Object.keys(snapshot.investigations).length}, evidence: ${Object.values(snapshot.evidence).flat().length}, analyses: ${snapshot.analysisResults.length}, reports: ${snapshot.reports.length}`)
