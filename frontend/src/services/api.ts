// =============================================================================
// PROJECT NEXUS AI - API Service Layer
// =============================================================================
// All API calls go through the backend. No direct database access from frontend.
// =============================================================================

import axios, { AxiosError, AxiosInstance } from 'axios'

const API_BASE_URL = (import.meta as any).env.VITE_API_BASE_URL || '/api'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Send cookies (httpOnly auth tokens)
})

// Request handler - no auth token in headers (using httpOnly cookies)
// We don't expose tokens to JavaScript

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle 401 - redirect to login
    if (error.response?.status === 401) {
      // Don't auto-redirect here; let components handle it
    }
    return Promise.reject(error)
  },
)

// =============================================================================
// Types
// =============================================================================

export interface User {
  id: string
  full_name: string
  email: string
  role: string
  is_active: boolean
  is_verified: boolean
  mfa_enabled: boolean
  created_at: string
}

export interface CaseItem {
  id: string
  case_number: string
  title: string
  description?: string
  status: string
  owner_id: string
  created_at: string
}

export interface EvidenceFile {
  id: string
  original_filename: string
  file_size_bytes: number
  mime_type: string
  file_hash_sha256: string
  status: string
  uploaded_at: string
  processed_at?: string
}

export interface AuthResponse {
  user: User
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// =============================================================================
// Auth API
// =============================================================================

export const authAPI = {
  register: (data: {
    full_name: string
    email: string
    password: string
    confirm_password: string
    accept_terms: boolean
    accept_privacy: boolean
  }) => apiClient.post<{ user: User }>('/auth/register', data),

  login: (data: { email: string; password: string }) =>
    apiClient.post<TokenResponse>('/auth/login', data),

  logout: () => apiClient.post('/auth/logout'),

  verifyEmail: (token: string) =>
    apiClient.get(`/auth/verify-email?token=${encodeURIComponent(token)}`),

  resendVerification: (email: string) =>
    apiClient.post('/auth/resend-verification', { email }),

  forgotPassword: (email: string) =>
    apiClient.post('/auth/forgot-password', { email }),

  resetPassword: (data: { token: string; new_password: string }) =>
    apiClient.post('/auth/reset-password', data),

  changePassword: (data: {
    current_password: string
    new_password: string
  }) => apiClient.post('/auth/change-password', data),

  getProfile: () => apiClient.get<User>('/auth/me'),

  updateProfile: (data: {
    full_name?: string
    institution?: string
    role_in_org?: string
    forensic_interest?: string
  }) => apiClient.patch<User>('/auth/me', data),

  refreshToken: () => apiClient.post<TokenResponse>('/auth/refresh'),
}

// =============================================================================
// Case API
// =============================================================================

export const casesAPI = {
  create: (data: {
    case_number: string
    title: string
    description?: string
  }) => apiClient.post<CaseItem>('/cases', data),

  list: (params?: { status?: string; limit?: number; offset?: number }) =>
    apiClient.get<CaseItem[]>('/cases', { params }),

  get: (caseId: string) => apiClient.get<CaseItem>(`/cases/${caseId}`),

  update: (caseId: string, data: { title: string; description?: string }) =>
    apiClient.patch<CaseItem>(`/cases/${caseId}`, data),

  delete: (caseId: string) => apiClient.delete(`/cases/${caseId}`),
}

// =============================================================================
// Evidence API
// =============================================================================

export const evidenceAPI = {
  upload: (caseId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<EvidenceFile>(`/evidence/upload?case_id=${caseId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: (caseId: string) => apiClient.get<EvidenceFile[]>(`/evidence/case/${caseId}`),
}

// =============================================================================
// ECHO - Evidence Gap Discovery
// =============================================================================

export const echoAPI = {
  createGap: (caseId: string, data: {
    gap_description: string
    suggested_evidence?: string
    priority?: string
  }) => apiClient.post(`/echo/cases/${caseId}/gaps`, data),

  listGaps: (caseId: string) => apiClient.get(`/echo/cases/${caseId}/gaps`),
}

// =============================================================================
// MOSAIC - Scenario Reconstruction
// =============================================================================

export const mosaicAPI = {
  createScenario: (caseId: string, data: {
    scenario_name: string
    scenario_description: string
    confidence_level?: string
  }) => apiClient.post(`/mosaic/cases/${caseId}/scenarios`, data),

  listScenarios: (caseId: string) =>
    apiClient.get(`/mosaic/cases/${caseId}/scenarios`),
}

// =============================================================================
// TIMEGLASS - Temporal Analysis
// =============================================================================

export const timeglassAPI = {
  createEvent: (caseId: string, data: {
    event_timestamp: string
    event_description: string
    source_evidence_id?: string
  }) => apiClient.post(`/timeglass/cases/${caseId}/events`, data),

  listEvents: (caseId: string) =>
    apiClient.get(`/timeglass/cases/${caseId}/events`),
}

// =============================================================================
// Chatbot
// =============================================================================

export const chatbotAPI = {
  createConversation: (data?: { title?: string; case_id?: string }) =>
    apiClient.post('/chatbot/conversations', data || {}),

  listConversations: () => apiClient.get('/chatbot/conversations'),

  getMessages: (conversationId: string) =>
    apiClient.get(`/chatbot/conversations/${conversationId}/messages`),

  sendMessage: (conversationId: string, content: string) =>
    apiClient.post(`/chatbot/conversations/${conversationId}/messages`, { content }),
}

// =============================================================================
// Reports
// =============================================================================

export const reportsAPI = {
  create: (caseId: string, data: {
    report_title: string
    report_content: string
  }) => apiClient.post(`/reports/cases/${caseId}`, data),

  list: (caseId: string) => apiClient.get(`/reports/cases/${caseId}`),
}

// =============================================================================
// Consent
// =============================================================================

export const consentAPI = {
  record: (purpose: string, granted: boolean) =>
    apiClient.post(`/consent/${purpose}`, { purpose, granted }),

  list: () => apiClient.get('/consent'),

  getAIProcessingPreference: () =>
    apiClient.get<{ external_ai_processing_enabled: boolean }>(
      '/consent/preference/external_ai_processing'
    ),
}

// =============================================================================
// Onboarding
// =============================================================================

export const onboardingAPI = {
  getStatus: () => apiClient.get('/onboarding/status'),
  complete: () => apiClient.post('/onboarding/complete'),
  setupProfile: (data: {
    full_name: string
    institution?: string
    role?: string
    forensic_interest?: string
  }) => apiClient.post('/onboarding/profile', data),
}
