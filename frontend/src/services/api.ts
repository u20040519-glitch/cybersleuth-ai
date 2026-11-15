// =============================================================================
// CYBERSLEUTH AI - API Service Layer
// =============================================================================
// Typed wrappers around the CyberSleuth AI backend. No secrets are exposed
// here: authentication uses short-lived access tokens issued by the backend
// and stored in the browser's localStorage; the refresh token is used only to
// obtain a new access token on 401.
// =============================================================================

import axios, { AxiosError, AxiosInstance } from 'axios'

const API_BASE_URL =
  (import.meta as any).env.VITE_API_BASE_URL?.trim() || '/api'

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

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Attach the bearer token on every request.
apiClient.interceptors.request.use((config) => {
  const token = tokenStore.access
  if (token) {
    config.headers = config.headers ?? {}
    ;(config.headers as any).Authorization = `Bearer ${token}`
  }
  return config
})

// On 401, try one refresh, then retry the original request once.
let refreshInFlight: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  const refreshToken = tokenStore.refresh
  if (!refreshToken) return false
  try {
    const response = await axios.post(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { 'Content-Type': 'application/json' }, timeout: 10000 },
    )
    tokenStore.save(response.data.access_token, response.data.refresh_token)
    return true
  } catch {
    tokenStore.clear()
    return false
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as any
    if (error.response?.status === 401 && original && !original.__retried) {
      original.__retried = true
      refreshInFlight = refreshInFlight ?? tryRefresh()
      const refreshed = await refreshInFlight
      refreshInFlight = null
      if (refreshed) {
        original.headers = original.headers ?? {}
        original.headers.Authorization = `Bearer ${tokenStore.access}`
        return apiClient(original)
      }
      window.dispatchEvent(new Event('auth:unauthorized'))
    }
    return Promise.reject(error)
  },
)

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export const authAPI = {
  login: (email: string, password: string) =>
    apiClient.post<any>('/auth/login', { email, password }),
  register: (data: {
    full_name: string
    email: string
    password: string
    confirm_password: string
    role?: string
  }) => apiClient.post<any>('/auth/register', data),
  logout: () => apiClient.post<any>('/auth/logout'),
  me: () => apiClient.get<any>('/auth/me'),
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export const dashboardAPI = {
  stats: () => apiClient.get<any>('/dashboard/stats'),
}

// ---------------------------------------------------------------------------
// Investigations
// ---------------------------------------------------------------------------
export const investigationsAPI = {
  list: () => apiClient.get<any[]>('/investigations'),
  get: (id: string) => apiClient.get<any>(`/investigations/${id}`),
  create: (data: any) => apiClient.post<any>('/investigations', data),
  update: (id: string, data: any) => apiClient.patch<any>(`/investigations/${id}`, data),
  remove: (id: string) => apiClient.delete<any>(`/investigations/${id}`),
  members: (id: string) => apiClient.get<any[]>(`/investigations/${id}/members`),
  addMember: (id: string, userId: string, role = 'member') =>
    apiClient.post<any>(`/investigations/${id}/members`, { user_id: userId, member_role: role }),
}

// ---------------------------------------------------------------------------
// Evidence
// ---------------------------------------------------------------------------
export const evidenceAPI = {
  list: (params?: { investigation_id?: string }) =>
    apiClient.get<any[]>('/evidence', { params }),
  upload: (file: File, investigationId: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('investigation_id', investigationId)
    return apiClient.post<any>('/evidence/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  },
  get: (id: string) => apiClient.get<any>(`/evidence/${id}`),
  download: (id: string) =>
    apiClient.get(`/evidence/${id}/download`, { responseType: 'blob', timeout: 300000 }),
  integrityCheck: (id: string) => apiClient.post<any>(`/evidence/${id}/integrity-check`),
  custody: (id: string) => apiClient.get<any[]>(`/evidence/${id}/custody`),
  verifyCustody: (id: string) => apiClient.get<any>(`/evidence/${id}/custody/verify`),
  events: (id: string) => apiClient.get<any[]>(`/evidence/${id}/events`),
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------
export const analysisAPI = {
  deeptrace: (evidenceId: string, options?: any) =>
    apiClient.post<any>('/deeptrace/analyze', { evidence_id: evidenceId, options: options ?? {} }, { timeout: 300000 }),
  spytrace: (evidenceId: string, options?: any) =>
    apiClient.post<any>('/spytrace/analyze', { evidence_id: evidenceId, options: options ?? {} }, { timeout: 300000 }),
  voiceproof: (evidenceId: string, options?: any) =>
    apiClient.post<any>('/voiceproof/analyze', { evidence_id: evidenceId, options: options ?? {} }, { timeout: 300000 }),
  cybersleuth: (evidenceId: string, options?: any) =>
    apiClient.post<any>('/cybersleuth/analyze', { evidence_id: evidenceId, options: options ?? {} }, { timeout: 300000 }),
  results: (params?: { investigation_id?: string; evidence_id?: string; module?: string; limit?: number }) =>
    apiClient.get<any[]>('/analysis/results', { params }),
  result: (id: string) => apiClient.get<any>(`/analysis/results/${id}`),
}

// ---------------------------------------------------------------------------
// Correlation
// ---------------------------------------------------------------------------
export const correlationAPI = {
  analyze: (investigationId: string) =>
    apiClient.post<any>(`/correlation/${investigationId}`, {}, { timeout: 300000 }),
  get: (investigationId: string) =>
    apiClient.get<any>(`/correlation/${investigationId}`, { timeout: 300000 }),
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------
export const reportsAPI = {
  generate: (investigationId: string, title?: string) =>
    apiClient.post<any>(`/reports/${investigationId}`, title ? { title } : {}, { timeout: 300000 }),
  list: (investigationId?: string) =>
    apiClient.get<any[]>('/reports', { params: investigationId ? { investigation_id: investigationId } : {} }),
  get: (id: string) => apiClient.get<any>(`/reports/${id}`),
  download: (id: string) =>
    apiClient.get(`/reports/${id}/download`, { responseType: 'blob', timeout: 300000 }),
}

// ---------------------------------------------------------------------------
// Audit logs
// ---------------------------------------------------------------------------
export const auditAPI = {
  list: (params?: { action?: string; resource?: string; limit?: number; offset?: number }) =>
    apiClient.get<any[]>('/audit-logs', { params }),
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export const healthAPI = {
  check: () => apiClient.get<any>('/health'),
}
