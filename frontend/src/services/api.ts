// =============================================================================
// CYBERSLEUTH AI - API Service Layer
// =============================================================================
// Phase 1: Frontend UI. API client prepared for Supabase backend (Phase 2).
// No secrets are exposed here. GEMINI_API_KEY and service role keys remain
// backend-only.
// =============================================================================

import axios, { AxiosError, AxiosInstance } from 'axios'

// Base URL resolution:
//  - `VITE_API_BASE_URL` set  -> use it verbatim (production, e.g. https://api.host/api)
//  - unset / empty            -> use the relative '/api' path, which the Vite dev
//                                server proxies to http://localhost:8000.
// The relative default is what makes LAN and tunnel sharing work: the request is
// proxied through the machine running Vite instead of the viewer's own localhost.
const API_BASE_URL =
  (import.meta as any).env.VITE_API_BASE_URL?.trim() || '/api'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  // Fail fast instead of hanging: with no backend running, the dev proxy would
  // otherwise leave requests pending indefinitely and the UI stuck on "loading".
  timeout: 8000,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      window.dispatchEvent(new Event('auth:unauthorized'))
    }
    return Promise.reject(error)
  },
)

// Placeholder API shape. These are wired to real endpoints in Phase 2.
export const investigationsAPI = {
  list: () => apiClient.get<any[]>('/investigations'),
  get: (id: string) => apiClient.get<any>(`/investigations/${id}`),
  create: (data: any) => apiClient.post<any>('/investigations', data),
  update: (id: string, data: any) => apiClient.put<any>(`/investigations/${id}`, data),
}

export const evidenceAPI = {
  list: () => apiClient.get<any[]>('/evidence'),
  upload: (file: File, investigationId?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (investigationId) formData.append('investigation_id', investigationId)
    return apiClient.post<any>('/evidence/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  get: (id: string) => apiClient.get<any>(`/evidence/${id}`),
  integrityCheck: (id: string) => apiClient.post<any>(`/evidence/${id}/integrity-check`),
}

export const analysisAPI = {
  deeptrace: (data: any) => apiClient.post<any>('/deeptrace/analyze', data),
  spytrace: (data: any) => apiClient.post<any>('/spytrace/analyze', data),
  voiceproof: (data: any) => apiClient.post<any>('/voiceproof/analyze', data),
  cybersleuth: (data: any) => apiClient.post<any>('/cybersleuth/analyze', data),
  status: (jobId: string) => apiClient.get<any>(`/analysis/${jobId}/status`),
}

export const correlationAPI = {
  analyze: (investigationId: string) => apiClient.post<any>(`/correlation/${investigationId}`),
  get: (investigationId: string) => apiClient.get<any>(`/correlation/${investigationId}`),
}

export const reportsAPI = {
  generate: (investigationId: string) => apiClient.post<any>(`/reports/${investigationId}`),
  get: (id: string) => apiClient.get<any>(`/reports/${id}`),
}

export const auditAPI = {
  list: () => apiClient.get<any[]>('/audit-logs'),
}

export const healthAPI = {
  check: () => apiClient.get<any>('/health'),
}
