// =============================================================================
// CYBERSLEUTH AI - Post-build step
// =============================================================================
// GitHub Pages has no rewrite rules: every unknown path is answered with
// `404.html`. Copying the built `index.html` to `404.html` therefore turns
// that error page into the single-page application, and React Router reads
// the requested path from the address bar - so deep links such as
// /investigations/<uuid> work on GitHub Pages as well.
//
// Netlify and the Vite preview server do their own SPA fallback, so the
// extra file is harmless there.
//
// Usage: node scripts/postbuild.mjs [outDir]
// =============================================================================

import { copyFile, access } from 'node:fs/promises'
import { constants } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const outDir = process.argv[2] || 'dist'
const distDir = resolve(dirname(fileURLToPath(import.meta.url)), '..', outDir)

async function exists(path) {
  try {
    await access(path, constants.F_OK)
    return true
  } catch {
    return false
  }
}

const indexHtml = resolve(distDir, 'index.html')
const notFoundHtml = resolve(distDir, '404.html')

if (!(await exists(indexHtml))) {
  console.error(`[postbuild] ${indexHtml} is missing - did the build run?`)
  process.exit(1)
}

await copyFile(indexHtml, notFoundHtml)
console.log('[postbuild] wrote 404.html (SPA fallback for GitHub Pages)')
