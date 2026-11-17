// =============================================================================
// CYBERSLEUTH AI - API service layer (switch)
// =============================================================================
// Two interchangeable implementations, selected at build time:
//
//   live  (default) the FastAPI backend, reached through the runtime
//                    configuration (Netlify redirect, Vite proxy, tunnel)
//
//   demo  (VITE_DEMO_MODE=true) a static snapshot of the seeded case, baked
//                    into the bundle - used by the published GitHub Pages
//                    demo, which must work without the backend and without
//                    anybody keeping a machine on
//
// The pages import this module and never need to know which one is in use.
// =============================================================================

import * as live from './liveApi'
import * as demo from './demoApi'

export const DEMO_MODE =
  ((import.meta as any).env.VITE_DEMO_MODE ?? '').toString().toLowerCase() === 'true'

const impl = (DEMO_MODE ? demo : live) as typeof live

export const tokenStore = impl.tokenStore

export const authAPI = impl.authAPI
export const dashboardAPI = impl.dashboardAPI
export const investigationsAPI = impl.investigationsAPI
export const evidenceAPI = impl.evidenceAPI
export const analysisAPI = impl.analysisAPI
export const correlationAPI = impl.correlationAPI
export const reportsAPI = impl.reportsAPI
export const auditAPI = impl.auditAPI
export const healthAPI = impl.healthAPI
export const apiClient = impl.apiClient

export { apiBaseCandidates, SAME_ORIGIN_BASE } from './runtimeConfig'
