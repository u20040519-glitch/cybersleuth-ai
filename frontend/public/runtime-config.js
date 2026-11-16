// =============================================================================
// CYBERSLEUTH AI - Runtime configuration
// =============================================================================
// This file is served as a static asset (never bundled), so the deployment can
// point the app at a different API without rebuilding it. That matters for
// the public demo: the backend runs behind a tunnel whose address changes
// whenever it is restarted, and the tunnel can be repointed by editing this
// single file.
//
//   apiBaseUrl  the absolute URL of the API, including the /api prefix
//               (for example https://abc-def.trycloudflare.com/api).
//               Leave it empty to use the same origin as the page, which is
//               what the Netlify proxy and the Vite dev server do.
//
// The build-time variable VITE_API_BASE_URL is used when this file does not
// define apiBaseUrl.
// =============================================================================

window.__CYBERSLEUTH_CONFIG__ = {
  apiBaseUrl: '',
}
