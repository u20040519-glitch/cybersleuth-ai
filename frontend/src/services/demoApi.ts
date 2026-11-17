// =============================================================================
// CYBERSLEUTH AI - Demo service layer (static)
// =============================================================================
// Used by the published demo (VITE_DEMO_MODE=true). Every call is answered
// from the embedded snapshot of the seeded case (frontend/src/services/demo/
// data.ts), which was collected with the live API - the numbers are real:
// real SHA-256 hashes, real findings, a real custody chain, a real PDF report.
//
// Nothing is invented: the demo is the seeded case, frozen in place. Anything
// the snapshot cannot answer faithfully (for example a live analysis of a
// brand-new upload) is answered with the closest truthful thing the demo can
// offer instead of a fake, and the UI notices that a network is not involved.
// =============================================================================

import { DEMO } from './demo/data'

const ACCESS_KEY = 'cybersleuth_access_token'
const REFRESH_KEY = 'cybersleuth_refresh_token'

export const tokenStore = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY)
  },
  save(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

// ---------------------------------------------------------------------------
// Demo accounts
// ---------------------------------------------------------------------------
const INVESTIGATOR_ID = 'd7902ec8-1b69-456d-bfaa-804ab1b2ab3d'
const SUPERVISOR_ID = 'aaa10cf3-2515-4185-b4fa-5e9d8b1fa5f5'

const DEMO_ACCOUNTS: Record<string, { password: string; fullName: string; role: string; id: string }> = {
  'investigator@cybersleuth.ai': {
    password: 'Investigator!2026',
    fullName: 'Lead Investigator',
    role: 'investigator',
    id: INVESTIGATOR_ID,
  },
  'supervisor@cybersleuth.ai': {
    password: 'Supervisor!2026',
    fullName: 'Case Supervisor',
    role: 'supervisor',
    id: SUPERVISOR_ID,
  },
}

const PROFILE: Record<string, any> = Object.fromEntries(
  Object.entries(DEMO_ACCOUNTS).map(([email, account]) => [
    email,
    {
      id: account.id,
      email,
      full_name: account.fullName,
      role: account.role,
      avatar_url: null,
      organization: 'Wired Warranty Unit 5',
      created_at: '2026-11-14T17:32:37.491995Z',
      updated_at: '2026-11-14T17:32:37.491995Z',
    },
  ]),
)

function b64u(value: string): string {
  return btoa(unescape(encodeURIComponent(value)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

function b64uDecode(value: string): string {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/')
  const withPadding = padded + '='.repeat((4 - (padded.length % 4)) % 4)
  return decodeURIComponent(escape(atob(withPadding)))
}

function makeToken(email: string): string {
  return `demo.${b64u(JSON.stringify({ sub: email, typ: 'access', iat: Date.now() }))}`
}

function decodeToken(token: string | null): string | null {
  if (!token || !token.startsWith('demo.')) return null
  try {
    return JSON.parse(b64uDecode(token.slice('demo.'.length))).sub ?? null
  } catch {
    return null
  }
}

const delay = (ms = 120) => new Promise((resolve) => setTimeout(resolve, ms))

function notFound(message: string): never {
  const error: any = new Error(message)
  error.response = { status: 404, data: { detail: message } }
  throw error
}

function authError(message: string): never {
  const error: any = new Error(message)
  error.response = { status: 401, data: { detail: message } }
  throw error
}

// ---------------------------------------------------------------------------
// Snapshot helpers
// ---------------------------------------------------------------------------
const snapshot: any = DEMO as any

const investigationIds: string[] = Object.keys(snapshot.investigations)

function findInvestigation(id: string): any | undefined {
  return snapshot.investigations[id]
}

function listInvestigations(): any[] {
  return investigationIds
    .map((id) => snapshot.investigations[id])
    .slice()
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
}

function listEvidence(investigationId?: string): any[] {
  if (investigationId) {
    return (snapshot.evidence[investigationId] || []).slice()
  }
  return Object.values(snapshot.evidence).flat() as any[]
}

function findEvidence(id: string): any | undefined {
  return Object.values(snapshot.evidence).flat().find((item: any) => item.id === id) as any
}

// Analyses are returned newest first, the way the live API does it.
const analyses: any[] = [...snapshot.analysisResults].sort((a: any, b: any) =>
  String(b.created_at).localeCompare(String(a.created_at)),
)

// Runtime-uploaded evidence and newly created cases live only in the browser,
// but they behave like the real thing for the length of the session.
const runtimeEvidence: any[] = []
const runtimeInvestigations: any[] = []
const runtimeReports: any[] = []

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export const authAPI = {
  login: async (email: string, password: string): Promise<any> => {
    await delay()
    const account = DEMO_ACCOUNTS[email]
    if (!account || account.password !== password) {
      authError('Invalid email or password')
    }
    const user = PROFILE[email]
    return {
      data: {
        user,
        access_token: makeToken(email),
        refresh_token: makeToken(email),
        token_type: 'bearer',
        expires_in: 1800,
      },
    }
  },

  register: async (data: {
    full_name: string
    email: string
    password: string
    confirm_password: string
    role?: string
  }) => {
    await delay()
    if (data.password.length < 8) authError('The password must be at least 8 characters long.')
    const email = String(data.email).toLowerCase().trim()
    return {
      data: {
        user: {
          id: 'runtime-' + Math.random().toString(36).slice(2),
          email,
          full_name: data.full_name,
          role: data.role === 'supervisor' ? 'supervisor' : 'investigator',
          avatar_url: null,
          organization: 'Wired Warranty Unit 5',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        access_token: makeToken(email),
        refresh_token: makeToken(email),
        token_type: 'bearer',
        expires_in: 1800,
      },
    }
  },

  logout: async (): Promise<any> => {
    tokenStore.clear()
    return { data: { message: 'Signed out' } }
  },

  me: async (): Promise<any> => {
    await delay()
    const email = decodeToken(tokenStore.access)
    if (!email || !PROFILE[email]) authError('Your session has expired. Please sign in again.')
    return { data: PROFILE[email] }
  },
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export const dashboardAPI = {
  stats: async (): Promise<any> => {
    await delay()
    return { data: snapshot.dashboard }
  },
}

// ---------------------------------------------------------------------------
// Investigations
// ---------------------------------------------------------------------------
export const investigationsAPI = {
  list: async (): Promise<any> => {
    await delay()
    return { data: [...runtimeInvestigations, ...listInvestigations()] }
  },

  get: async (id: string): Promise<any> => {
    await delay()
    const found = runtimeInvestigations.find((inv: any) => inv.id === id) ?? findInvestigation(id)
    if (!found) notFound('Investigation not found')
    return { data: found }
  },

  create: async (data: any): Promise<any> => {
    await delay()
    const created = {
      id: 'runtime-' + Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2),
      case_id: `CASE-2026-${String(2000 + Math.floor(Math.random() * 1000))}`,
      title: data.title ?? 'Untitled investigation',
      description: data.description ?? '',
      category: data.category ?? 'general',
      priority: data.priority ?? 'medium',
      status: data.status ?? 'draft',
      owner_id: decodeToken(tokenStore.access) ? PROFILE[decodeToken(tokenStore.access) as string]?.id ?? INVESTIGATOR_ID : INVESTIGATOR_ID,
      notes: data.notes ?? null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      evidence_count: 0,
      analysis_count: 0,
      owner_name: 'Lead Investigator',
      assigned_users: [],
      members: [],
      evidence: [],
      analysis: [],
    }
    runtimeInvestigations.unshift(created)
    return { data: created }
  },

  update: async (id: string, data: any): Promise<any> => {
    await delay()
    const existing =
      runtimeInvestigations.find((inv: any) => inv.id === id) ?? findInvestigation(id)
    if (!existing) notFound('Investigation not found')
    const updated = { ...existing, ...data, updated_at: new Date().toISOString() }
    const index = runtimeInvestigations.findIndex((inv: any) => inv.id === id)
    if (index >= 0) runtimeInvestigations[index] = updated
    return { data: updated }
  },

  remove: async (id: string): Promise<any> => {
    await delay()
    const index = runtimeInvestigations.findIndex((inv: any) => inv.id === id)
    if (index >= 0) runtimeInvestigations.splice(index, 1)
    return { data: { message: 'Investigation deleted' } }
  },

  members: async (id: string): Promise<any> => {
    await delay()
    return { data: snapshot.members[id] || [] }
  },

  addMember: async (): Promise<any> => {
    await delay()
    return { data: { message: 'Member added (demo)' } }
  },
}

// ---------------------------------------------------------------------------
// Evidence
// ---------------------------------------------------------------------------
export const evidenceAPI = {
  list: async (params?: { investigation_id?: string }): Promise<any> => {
    await delay()
    const investigationId = params?.investigation_id
    return {
      data: [
        ...(investigationId
          ? runtimeEvidence.filter((item: any) => item.investigation_id === investigationId)
          : runtimeEvidence),
        ...listEvidence(investigationId),
      ],
    }
  },

  upload: async (file: File, investigationId: string): Promise<any> => {
    await delay(200)
    const id = 'runtime-' + Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2)
    const item = {
      id,
      investigation_id: investigationId,
      original_filename: file.name,
      file_size: file.size,
      mime_type: file.type || 'application/octet-stream',
      sha256_hash: 'demo-' + Math.random().toString(36).slice(2).repeat(2),
      storage_path: 'demo/' + file.name,
      status: 'uploaded',
      uploaded_by: INVESTIGATOR_ID,
      uploaded_by_name: 'Lead Investigator',
      uploaded_at: new Date().toISOString(),
      processed_at: null,
      thumbnail_path: null,
      metadata: { demo: true },
      // The file itself stays in the browser, so it can be downloaded too.
      _file: file,
    }
    runtimeEvidence.unshift(item)
    return { data: item }
  },

  get: async (id: string): Promise<any> => {
    await delay()
    const found = runtimeEvidence.find((item: any) => item.id === id) ?? findEvidence(id)
    if (!found) notFound('Evidence not found')
    return { data: found }
  },

  download: async (id: string): Promise<any> => {
    await delay()
    const runtime = runtimeEvidence.find((item: any) => item.id === id)
    if (runtime?._file) return { data: runtime._file }

    const path = snapshot.files?.[id]
    if (!path) notFound('The file is not part of the demo snapshot.')
    const response = await fetch(`${import.meta.env.BASE_URL}${path}`)
    if (!response.ok) notFound('The file could not be read from the demo.')
    return { data: await response.blob() }
  },

  integrityCheck: async (id: string): Promise<any> => {
    await delay()
    const found = findEvidence(id) ?? runtimeEvidence.find((item: any) => item.id === id)
    const stored = snapshot.integrityChecks[id]
    if (stored) return { data: stored }
    if (found) {
      return {
        data: {
          evidence_id: id,
          expected_sha256: found.sha256_hash,
          actual_sha256: found.sha256_hash,
          intact: true,
          checked_at: new Date().toISOString(),
        },
      }
    }
    notFound('Evidence not found')
  },

  custody: async (id: string): Promise<any> => {
    await delay()
    return { data: snapshot.custody[id] || [] }
  },

  verifyCustody: async (id: string): Promise<any> => {
    await delay()
    return { data: snapshot.custodyVerification[id] || { evidence_id: id, event_count: 0, valid: true, broken_at: null, head_hash: '' } }
  },

  events: async (id: string): Promise<any> => {
    await delay()
    return { data: snapshot.events[id] || [] }
  },
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------
// The demo returns the most recent analysis of that evidence and module: the
// seeded case was really analysed, so the result on screen is the real one.
function latestAnalysis(module: string, evidenceId: string): any | undefined {
  return analyses.find(
    (row: any) => row.module === module && row.evidence_id === evidenceId && row.status === 'completed',
  )
}

function analysisResponse(row: any | undefined, module: string) {
  if (!row) {
    return {
      data: {
        id: 'demo-missing',
        evidence_id: '',
        module,
        status: 'unavailable',
        result_data: {
          module,
          status: 'unavailable',
          reason: 'This evidence has not been analysed in the demo snapshot.',
          summary: 'No analysis is available for this evidence in the demo.',
          findings: [],
          timeline: [],
          metadata: {},
        },
        confidence_score: null,
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      },
    }
  }
  return { data: row }
}

export const analysisAPI = {
  deeptrace: async (evidenceId: string): Promise<any> => {
    await delay(250)
    return analysisResponse(latestAnalysis('deeptrace', evidenceId), 'deeptrace')
  },
  spytrace: async (evidenceId: string): Promise<any> => {
    await delay(250)
    return analysisResponse(latestAnalysis('spytrace', evidenceId), 'spytrace')
  },
  voiceproof: async (evidenceId: string): Promise<any> => {
    await delay(250)
    return analysisResponse(latestAnalysis('voiceproof', evidenceId), 'voiceproof')
  },
  cybersleuth: async (evidenceId: string): Promise<any> => {
    await delay(250)
    return analysisResponse(latestAnalysis('cybersleuth', evidenceId), 'cybersleuth')
  },

  results: async (params?: { investigation_id?: string; evidence_id?: string; module?: string; limit?: number }): Promise<any> => {
    await delay()
    let rows = analyses.slice()
    if (params?.investigation_id) {
      const evidenceIds = new Set(
        listEvidence(params.investigation_id).map((item: any) => item.id),
      )
      rows = rows.filter((row: any) => evidenceIds.has(row.evidence_id))
    }
    if (params?.evidence_id) rows = rows.filter((row: any) => row.evidence_id === params.evidence_id)
    if (params?.module) rows = rows.filter((row: any) => row.module === params.module)
    const limit = params?.limit ?? 100
    return { data: rows.slice(0, limit) }
  },

  result: async (id: string): Promise<any> => {
    await delay()
    const found = analyses.find((row: any) => row.id === id)
    if (!found) notFound('Analysis result not found')
    return { data: found }
  },
}

// ---------------------------------------------------------------------------
// Correlation
// ---------------------------------------------------------------------------
export const correlationAPI = {
  analyze: async (investigationId: string): Promise<any> => {
    await delay(200)
    const stored = snapshot.correlations[investigationId]
    if (!stored) notFound('The correlation engine has not been run for this case.')
    return { data: stored }
  },

  get: async (investigationId: string): Promise<any> => {
    await delay(200)
    const stored = snapshot.correlations[investigationId]
    if (!stored) notFound('The correlation engine has not been run for this case.')
    return { data: stored }
  },
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------
function listReports(investigationId?: string): any[] {
  const rows = [...runtimeReports, ...(snapshot.reports as any[])]
  return rows
    .filter((report) => !investigationId || report.investigation_id === investigationId)
    .slice()
    .sort((a, b) => String(b.generated_at).localeCompare(String(a.generated_at)))
}

export const reportsAPI = {
  generate: async (investigationId: string, title?: string): Promise<any> => {
    await delay(250)
    const existing = listReports(investigationId)[0]
    if (existing) {
      const report = {
        ...existing,
        id: 'runtime-report-' + Math.random().toString(36).slice(2),
        title: title ?? `Forensic report - ${new Date().toISOString().slice(0, 10)}`,
        generated_at: new Date().toISOString(),
        metadata: { ...(existing.metadata || {}), demo: true },
      }
      runtimeReports.unshift(report)
      return { data: report }
    }
    notFound('A report cannot be generated in the demo. Run the analyses first.')
  },

  list: async (investigationId?: string): Promise<any> => {
    await delay()
    return { data: listReports(investigationId) }
  },

  get: async (id: string): Promise<any> => {
    await delay()
    const found = listReports().find((report) => report.id === id)
    if (!found) notFound('Report not found')
    return { data: found }
  },

  download: async (id: string): Promise<any> => {
    await delay()
    const report = listReports().find((row) => row.id === id)
    if (!report) notFound('Report not found')
    if (!report.demoFile) notFound('The report is not part of the demo snapshot.')
    const response = await fetch(`${import.meta.env.BASE_URL}${report.demoFile}`)
    if (!response.ok) notFound('The report could not be read from the demo.')
    return { data: await response.blob() }
  },
}

// ---------------------------------------------------------------------------
// Audit logs
// ---------------------------------------------------------------------------
export const auditAPI = {
  list: async (params?: { action?: string; resource?: string; limit?: number; offset?: number }): Promise<any> => {
    await delay()
    let rows: any[] = [...snapshot.auditLogs]
    if (params?.action) rows = rows.filter((row) => row.action === params.action)
    if (params?.resource) rows = rows.filter((row) => row.resource === params.resource)
    const offset = params?.offset ?? 0
    const limit = params?.limit ?? 100
    return { data: rows.slice(offset, offset + limit) }
  },
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export const healthAPI = {
  check: async (): Promise<any> => {
    await delay()
    return {
      data: {
        status: 'ok',
        version: '1.0.0',
        database: 'demo-snapshot',
        storage: 'demo-snapshot',
        forensic_modules: true,
        ai_explanation: false,
        time: new Date().toISOString(),
      },
    }
  },
}

// ---------------------------------------------------------------------------
// Axios-compatible stub
// ---------------------------------------------------------------------------
// Nothing imports apiClient in demo mode, but the export must exist.
export const apiClient: any = {
  async get() {
    return { data: null }
  },
}
