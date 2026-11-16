// =============================================================================
// CYBERSLEUTH AI - Runtime configuration
// =============================================================================
// This file is served as a static asset (never bundled), so the deployment can
// point the app at a different API without rebuilding it. That matters for
// the public demo: the backend runs behind a tunnel whose address changes
// whenever it is restarted, and the address can be repointed by replacing
// this single file.
//
//   apiBaseUrls  the API addresses to try, in order. The first one that
//                 answers `/health` is used, so a stale address falls through
//                 to the next one instead of breaking the app. '/api' is the
//                 same origin and is always added as the last candidate.
//
// The build-time variable VITE_API_BASE_URL is used when this file does not
// list any address.
// =============================================================================

window.__CYBERSLEUTH_CONFIG__ = {
  apiBaseUrls: ['/api'],
}
